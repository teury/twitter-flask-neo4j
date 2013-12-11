# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application written with Flask and Neo4j.

    :copyright: (c) 2010 by Armin Ronacher.
    :copyright: (c) 2013 by Vahid chakoshy.
    :license: BSD, see LICENSE for more details.
"""

import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash

from models import User, Post

# configuration
#DATABASE = '/tmp/minitwit.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)


def get_user_id(username):
    user_id = User.get_user_id(username)
    print "user_id", user_id
    
    return user_id if user_id else None


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.before_request
def before_request():
    g.user = None
    
    if 'user_id' in session:
        g.user = User.get_user_by_id(session['user_id'])  


@app.route('/')
def timeline():
    """Shows a users timeline or if no user is logged in it will
    redirect to the public timeline.  This timeline shows the user's
    messages as well as all the messages of followed users.
    """
    if not g.user:
        return redirect(url_for('public_timeline'))
    
    messages = Post.timeline_following(g.user._id)
    recommend_user = User.recommend_user(g.user._id)

    return render_template('timeline.html', messages=messages, ru=recommend_user)


@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    messages = Post.timeline()    
    return render_template('timeline_public.html', messages=messages)


@app.route('/like/<post_id>')
def like(post_id):
    if not g.user:
        abort(503)

    Post.like(post_id, g.user._id)
    return 'liked'

@app.route('/<username>')
def user_timeline(username):
    """Display's a users tweets."""
    profile_user = User.get_user_by_name(username=username)
    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = User.followed(g.user._id, profile_user._id)
    messages = Post.timeline_user(profile_user._id)
    return render_template('timeline.html', messages=messages, followed=followed,
            profile_user=profile_user)


@app.route('/following')
def following_by_me():
    if not g.user:
        abort(401)

    following = User.following_by_user(g.user._id)
    return render_template('following.html', following=following)

@app.route('/followed')
def followed():
    if not g.user:
        abort(401)

    followed = User.followed_by_user(g.user._id)
    return render_template('followed.html', following=followed)


@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)

    User.following(g.user._id, whom_id)
    flash('You are now following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Removes the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    
    User.unfollowing(g.user._id, whom_id)

    flash('You are no longer following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/add_message', methods=['POST'])
def add_message():
    """Registers a new message for the user."""
    if 'user_id' not in session:
        abort(401)
    if request.form['text']:
        user_id = session['user_id']
        text = request.form['text']
        date = int(time.time())

        Post.create(text=text, date=date, user_id=user_id)

        """
        db = get_db()
        db.execute('''insert into message (author_id, text, pub_date)
          values (?, ?, ?)''', (session['user_id'], request.form['text'],
                                int(time.time())))
        db.commit()
        """
        flash('Your message was recorded')
    return redirect(url_for('timeline'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        user = User.login(username=request.form['username'])
        print "user is", user
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['password'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user._id
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            user = User.register(username=request.form['username'],
                          email=request.form['email'],
                          password=generate_password_hash(request.form['password']))
            """
            db = get_db()
            db.execute('''insert into user (
              username, email, pw_hash) values (?, ?, ?)''',
              [request.form['username'], request.form['email'],
               generate_password_hash(request.form['password'])])
            db.commit()
            """
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('public_timeline'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url


if __name__ == '__main__':
    #init_db()
    app.run()
