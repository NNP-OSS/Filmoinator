import os
import uuid
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, make_response, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'postgresql://filmoinator:filmoinator_secret@db:5432/filmoinator'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

db = SQLAlchemy(app)


class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    submitted_by = db.Column(db.String(100), default='anonymous')
    round_added = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Round(db.Model):
    __tablename__ = 'rounds'
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer, unique=True, nullable=False)
    phase = db.Column(db.String(20), nullable=False, default='submission')
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id', ondelete='CASCADE'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    visitor_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=text('CURRENT_TIMESTAMP'))
    __table_args__ = (db.UniqueConstraint('round_number', 'visitor_id'),)


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer, nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=text('CURRENT_TIMESTAMP'))
    __table_args__ = (db.UniqueConstraint('round_number', 'position'),)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def get_visitor_id():
    return request.cookies.get('visitor_id')


def get_active_round():
    return Round.query.filter_by(is_active=True).first()


def count_votes(round_number):
    results = db.session.query(
        Vote.movie_id,
        Movie.title,
        db.func.count(Vote.id).label('votes')
    ).join(Movie, Vote.movie_id == Movie.id)\
     .filter(Vote.round_number == round_number)\
     .group_by(Vote.movie_id, Movie.title)\
     .order_by(db.func.count(Vote.id).desc())\
     .all()
    return results


def advance_round(current_round):
    top_n = {1: 3, 2: 2, 3: 1}.get(current_round, 1)
    vote_counts = count_votes(current_round)
    advancing = vote_counts[:top_n]

    Result.query.filter_by(round_number=current_round).delete()
    for pos, (movie_id, title, votes) in enumerate(advancing, 1):
        r = Result(round_number=current_round, movie_id=movie_id, position=pos)
        db.session.add(r)

    old_round = Round.query.filter_by(round_number=current_round).first()
    if old_round:
        old_round.phase = 'closed'
        old_round.is_active = False

    next_round_num = current_round + 1
    if next_round_num <= 3:
        next_round = Round.query.filter_by(round_number=next_round_num).first()
        if next_round:
            next_round.phase = 'pending'
            next_round.is_active = True

        advancing_ids = [m[0] for m in advancing]
        Movie.query.filter(Movie.id.notin_(advancing_ids), Movie.round_added == current_round).delete()
        for mid in advancing_ids:
            m = Movie.query.get(mid)
            if m:
                m.round_added = next_round_num

    db.session.commit()
    return advancing


# ---------- User routes ----------

@app.route('/')
def index():
    active_round = get_active_round()

    visitor_id = get_visitor_id()
    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    has_voted = False
    if visitor_id:
        existing = Vote.query.filter_by(
            round_number=active_round.round_number, visitor_id=visitor_id
        ).first() if active_round else None
        has_voted = existing is not None

    resp = None

    if not active_round:
        winner = Result.query.filter_by(round_number=3).first()
        if winner:
            movie = Movie.query.get(winner.movie_id)
            resp = make_response(render_template('index.html', phase='finished', movie=movie))
        else:
            resp = make_response(render_template('index.html', phase='no_active_round'))
        resp.set_cookie('visitor_id', visitor_id, max_age=86400 * 365)
        return resp

    if active_round.phase == 'submission':
        movies = Movie.query.filter_by(round_added=active_round.round_number).all()
        resp = make_response(render_template('index.html', phase='submission',
                              round=active_round, movies=movies))

    elif active_round.phase == 'voting':
        if active_round.round_number == 1:
            movies = Movie.query.filter_by(round_added=1).all()
        else:
            prev = Result.query.filter_by(round_number=active_round.round_number - 1).all()
            movie_ids = [r.movie_id for r in prev]
            movies = Movie.query.filter(Movie.id.in_(movie_ids)).all()

        resp = make_response(render_template('index.html', phase='voting', round=active_round,
                               movies=movies, has_voted=has_voted))

    elif active_round.phase in ('closed', 'pending'):
        prev_round = active_round.round_number
        if active_round.phase == 'pending':
            prev_round = active_round.round_number - 1
        results = Result.query.filter_by(round_number=prev_round).order_by(Result.position).all()
        movie_map = {}
        for r in results:
            movie = Movie.query.get(r.movie_id)
            if movie:
                movie_map[r.position] = movie
        resp = make_response(render_template('index.html', phase='closed',
                              round=active_round, results=results, movie_map=movie_map,
                              result_round=prev_round))

    if not resp:
        resp = make_response(render_template('index.html', phase='no_active_round'))

    resp.set_cookie('visitor_id', visitor_id, max_age=86400 * 365)
    return resp


@app.route('/submit', methods=['POST'])
def submit_movie():
    active_round = get_active_round()
    if not active_round or active_round.phase != 'submission':
        flash('Dodawanie filmów nie jest teraz aktywne.', 'error')
        return redirect(url_for('index'))

    title = request.form.get('title', '').strip()
    if not title:
        flash('Podaj tytuł filmu.', 'error')
        return redirect(url_for('index'))

    existing = Movie.query.filter_by(title=title, round_added=active_round.round_number).first()
    if existing:
        flash('Ten film już został dodany w tej rundzie.', 'error')
        return redirect(url_for('index'))

    movie = Movie(title=title, submitted_by='anonymous', round_added=active_round.round_number)
    db.session.add(movie)
    db.session.commit()
    flash('Film został dodany!', 'success')
    return redirect(url_for('index'))


@app.route('/vote', methods=['POST'])
def vote():
    active_round = get_active_round()
    if not active_round or active_round.phase != 'voting':
        flash('Głosowanie nie jest teraz aktywne.', 'error')
        return redirect(url_for('index'))

    visitor_id = get_visitor_id()
    if not visitor_id:
        flash('Błąd identyfikatora. Spróbuj odświeżyć stronę.', 'error')
        return redirect(url_for('index'))

    existing = Vote.query.filter_by(
        round_number=active_round.round_number, visitor_id=visitor_id
    ).first()
    if existing:
        flash('Już głosowałeś w tej rundzie!', 'error')
        return redirect(url_for('index'))

    movie_id = request.form.get('movie_id')
    if not movie_id:
        flash('Wybierz film.', 'error')
        return redirect(url_for('index'))

    movie = Movie.query.get(int(movie_id))
    if not movie:
        flash('Nieprawidłowy film.', 'error')
        return redirect(url_for('index'))

    vote = Vote(movie_id=int(movie_id), round_number=active_round.round_number, visitor_id=visitor_id)
    db.session.add(vote)
    db.session.commit()
    flash('Głos został oddany!', 'success')
    return redirect(url_for('index'))


@app.route('/wyniki')
def wyniki():
    results = Result.query.filter_by(round_number=3).first()
    if results:
        movie = Movie.query.get(results.movie_id)
        return render_template('wyniki.html', movie=movie)

    prev_results = Result.query.order_by(Result.round_number.desc()).all()
    movie_map = {}
    round_info = {}
    for r in prev_results:
        m = Movie.query.get(r.movie_id)
        if m:
            movie_map[r.id] = m
        if r.round_number not in round_info:
            round_info[r.round_number] = []
        round_info[r.round_number].append(r)

    return render_template('wyniki.html', movie=None, round_info=round_info, movie_map=movie_map)


# ---------- Admin routes ----------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Nieprawidłowe dane logowania.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    active_round = get_active_round()
    rounds = Round.query.order_by(Round.round_number).all()
    movie_count = Movie.query.count()
    vote_count = Vote.query.count()

    vote_stats = []
    if active_round and active_round.phase == 'voting':
        vc = count_votes(active_round.round_number)
        for movie_id, title, cnt in vc:
            vote_stats.append({'title': title, 'votes': cnt})

    return render_template('admin/dashboard.html', active_round=active_round,
                           rounds=rounds, movie_count=movie_count,
                           vote_count=vote_count, vote_stats=vote_stats)


@app.route('/admin/round/next', methods=['POST'])
@admin_required
def admin_round_next():
    active_round = get_active_round()
    if not active_round:
        flash('Brak aktywnej rundy.', 'error')
        return redirect(url_for('admin_dashboard'))

    if active_round.phase == 'submission':
        movies = Movie.query.filter_by(round_added=active_round.round_number).count()
        if movies == 0:
            flash('Brak filmów w tej rundzie. Dodaj filmy przed rozpoczęciem głosowania.', 'error')
            return redirect(url_for('admin_dashboard'))
        active_round.phase = 'voting'
        db.session.commit()
        flash('Rozpoczęto głosowanie w rundzie ' + str(active_round.round_number) + '.', 'success')

    elif active_round.phase == 'voting':
        if active_round.round_number == 3:
            advancing = advance_round(3)
            flash('Wybrano zwycięzcę! Sprawdź wyniki.', 'success')
        else:
            advancing = advance_round(active_round.round_number)
            names = ', '.join(m[1] for m in advancing)
            flash(f'Runda {active_round.round_number} zakończona. Przechodzą: {names}', 'success')

    elif active_round.phase == 'closed':
        flash('Ta runda jest już zamknięta.', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/round/reset-votes', methods=['POST'])
@admin_required
def admin_reset_votes():
    active_round = get_active_round()
    if active_round and active_round.phase == 'voting':
        Vote.query.filter_by(round_number=active_round.round_number).delete()
        db.session.commit()
        flash('Wszystkie głosy w tej rundzie zostały zresetowane.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/movies')
@admin_required
def admin_movies():
    movies = Movie.query.order_by(Movie.round_added, Movie.title).all()
    return render_template('admin/movies.html', movies=movies)


@app.route('/admin/movies/delete/<int:movie_id>', methods=['POST'])
@admin_required
def admin_delete_movie(movie_id):
    movie = Movie.query.get(movie_id)
    if movie:
        Vote.query.filter_by(movie_id=movie_id).delete()
        Result.query.filter_by(movie_id=movie_id).delete()
        db.session.delete(movie)
        db.session.commit()
        flash('Film usunięty.', 'success')
    return redirect(url_for('admin_movies'))


@app.route('/admin/reset', methods=['POST'])
@admin_required
def admin_reset():
    db.session.query(Vote).delete()
    db.session.query(Result).delete()
    db.session.query(Movie).delete()
    db.session.query(Round).delete()
    db.session.commit()

    for rn in [1, 2, 3]:
        r = Round(round_number=rn, phase='submission' if rn == 1 else 'pending', is_active=(rn == 1))
        db.session.add(r)
    db.session.commit()
    flash('Wszystko zresetowane.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/round/start-voting', methods=['POST'])
@admin_required
def admin_start_voting():
    active_round = get_active_round()
    if active_round and active_round.phase == 'pending':
        active_round.phase = 'voting'
        db.session.commit()
        flash(f'Rozpoczęto głosowanie w rundzie {active_round.round_number}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/round/set-submission', methods=['POST'])
@admin_required
def admin_set_submission():
    active_round = get_active_round()
    if active_round:
        active_round.phase = 'submission'
        db.session.commit()
        flash('Zmieniono fazę na dodawanie filmów.', 'success')
    return redirect(url_for('admin_dashboard'))


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
