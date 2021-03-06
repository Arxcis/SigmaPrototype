#!usr/bin/env python3
# -*- coding:utf-8 -*-

"""
    Navn: __init__.py
    Prosjekt: SigmaPrototype
    Opprettet av: Jonas
    Beskrivelse: __init__.py fungerer som kontroller / API for hele Flask-applikasjonen.
                 En kontroller får input/request i form av en URL, f.eks www.google.com,
                  fra en klient. Kontrolleren bestemmer hva som skal returneres til klienten
                   for en gitt request.
                                         ----- Jonas -----


# --------------------------- CONTROLLER / API --------------------------------- #

# ------------------------------------------------------------------------------ #
| index | Route                          | Return value                          |
# ------------------------------------------------------------------------------ # 

    1.  /favicon.ico                   -> send_from_directory(static, favicon.ico)
    2.  /                              -> redirect(/login or /inputurl)
    3.  /logout                        -> redirect(/)
    4.  /login                         -> render_template(login.html)
    5.  /meny                          -> render_template(meny.html)
    6.  /inputurl                      -> render_template(input.html)
    7.  /maps                          -> render_template(maps.html, maps=maps)
    8.  /<user>/map/<mapid>            -> render_template(map.html)
    9.  /<user>/map/<mapid>/thumbnail  -> render_template(mapthumbnail.html)
    10. /mapssvg                       -> render_template(mapssvg.html)
    11. /postuser                      -> redirect(/inputurl)

    12. /postmeta                      -> jsonify(searchdata=searchdata)
    13. /getmap                        -> jsonify(map=the_map)
    14. /getmaps                       -> jsonify(map=maps)
    15. /mapnames                      -> jsonify(names=map_names)
    16. /updatemap                     -> jsonify(new=new)
    17. /relabeltopic                  -> jsonify()
    18. /fetchsearchdata               -> jsonify(searchdata=searchdata)    
    19. /tags                          -> jsonify(tags=tags)
    20. /deletelink                    -> jsonify()
    21. /fetchtitle                    -> jsonify(title=title)
    22. /fetchmeta                     -> jsonify(meta=meta.__dict__)
    23. /fetchlinks                    -> jsonify(links=links)

                                        * All jsonify return (status=status)
# ------------------------------------------------------------------------------ # 

"""

from flask import Flask, render_template, request, url_for, \
                   redirect, session, jsonify, send_from_directory
import os
import gc # flask and garbage collection is not a good combo, clear session should invite a gc.collect()
from functools import wraps
from  datetime import datetime
import time
import sigma

# for pickles sake...
from sigma import KnowledgeMap, Topic
import auth
from utility import load_config


app = Flask(__name__)   # - Initialize the Flask-app object
load_config(app)        # - Loads config 
                        # - Create a secret key to be used by session = {} 
                        #     to encrypt sensitive data


# ----------- LOGIN WRAP -----------

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'innlogget' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('index'))
    return wrap


###############################################################################
# ---------------------------- HTTP request ROUTES ---------------------------#
# --------------------------------------------------------------------------- #
# 
#    Every route is defined like this 
#    @app.route('/foo')
#    def foo():
#        return bar
#
#    To access a function, you send a HttpRequest with this url
#
#      http://www.barfoo.com + /foo 
#           http://localhost + /foo
#      
#      + additional POST or GET parameters if required by the function
#                                        
# --------------------------------------------------------------------------- #


# ------------------------------- MISC ROUTES ------------------------------- #

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')


@app.route('/')
def index():
    # ryddig.
    if 'innlogget' in session:
        return redirect(url_for('input_url'))
    else:
        return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():

    session.clear()
    gc.collect()  
    return redirect(url_for('index'))


# --------- RENDER TEMPLATE view ROUTES ------------

@app.route('/login')
def login():

    return render_template('login.html')


@app.route('/meny')
@login_required
def meny():

    return render_template('base.html')


@app.route('/inputurl')
@login_required
def input_url():

    user = session['user']
    searchdata = sigma.get_searchdata(user)

    return render_template('input.html', searchdata=searchdata)


@app.route('/maps')
@login_required
def maps():
    user = session['user']
    maps = sigma.get_maps(user).values()
    
    return render_template('maps.html', maps=maps)


@app.route('/<user>/map/<mapid>')
@login_required
def show_map(user, mapid):
    # the url is built with user added to it to
    # be ready for the future when we might dare to
    # share our maps.
    user = session['user']
    the_map = sigma.get_map(user, mapid)
    if the_map is None:
        return "There is no map with this main_topic"
    #the_map = sigma.KnowledgeMap("Python", "flask")
    return render_template('map.html', map=the_map)
 

@app.route('/<user>/map/<mapid>/thumbnail')
@login_required
def map_thumbnail(user, mapid):
    # the url is built with user added to it to
    # be ready for the future when we might dare to
    # share our maps.
    user = session['user']
    the_map = sigma.get_map(user, mapid)
    if the_map is None:
        return "There is no map with this main_topic"
    #the_map = sigma.KnowledgeMap("Python", "flask")
    return render_template('mapthumbnail.html', mapid=mapid)


@app.route('/mapssvg')
@login_required
def maps_svg():

    return render_template('mapssvg.html')


# --------- FORM POST request ROUTES -----------------

@app.route('/postuser', methods=['POST'])
def post_user():

    user = request.form.get('iUser', None)
    if (auth.authenticate(user, None)):
        session['innlogget'] = True
        session['user'] = user
        session['last_request'] = time.time()

    return redirect(url_for('input_url'))


# ---------- AJAX POST/GET request ROUTES -------------

@app.route('/postmeta', methods=['POST'])
@login_required
def post_meta():
    # POSTparamter is json = {url: '', meta : {<object>metainfo}}
    
    user = session['user']
    json = request.get_json()

    meta = json['meta']
    url = json['url']

    if url and meta:
        # Saves it in the users links file.
        try:
            sigma.save_link(id=url, meta=meta, user=user)
            searchdata = sigma.get_searchdata(user)
            return jsonify(status='Postmeta OK', searchdata=searchdata)

        except Exception as e:
            return jsonify(status='Postmeta ERROR:' + str(e))
    return 'Missing Url and Meta'


@app.route('/getmap', methods=['POST'])
@login_required
def get_map():

    user = session['user']
    
    try:
        mapid = request.form.get('main_topic', None)
        the_map = sigma.get_map(user, mapid, True) 

        return jsonify(status='Getmap OK', map=the_map)

    except Exception as e:
        return jsonify(status='Getmap ERROR:' + str(e))


@app.route('/getmaps', methods=['GET'])
@login_required
def get_maps():
    # NOT IMPLEMETNED, JSON SERIALIZING tecghnique missing.
    user = session['user']
    
    try:
        maps = sigma.get_maps(user, True) 
        return jsonify(status='Getmaps OK', map=maps)

    except Exception as e:
        return jsonify(status='Getmaps ERROR:' + str(e))


@app.route('/mapnames', methods=['GET'])
@login_required
def get_map_names():

    user = session['user']
    try:
        the_maps = sigma.get_maps(user)

        map_names = []
        for k in the_maps:
            map_names.append(k)

        return jsonify(status='Names OK', names=map_names)

    except Exception as e:
        return jsonify(status='Names ERROR:' + str(e))


@app.route('/updatemap', methods=['POST'])
@login_required
def update_map():
    # POSTparamter is json = {url: '', main_topic: '', subtopic: ''}

    user = session['user']
    json = request.get_json()
 
    try:
        url = json.get('url', None)
        main_topic = json['main_topic']
        subtopic = json['subtopic']

        new = sigma.update_map(user, main_topic, subtopic, url)
        return jsonify(status='Updatemap OK', new=new)
    except Exception as e:
        return jsonify(status='Updatemap ERROR: ' + str(e))


@app.route('/relabeltopic', methods=['POST'])
@login_required
def relabel_topic():
    user = session['user']
    json = request.get_json()

    try:
        map_id = json.get('map_id', None)
        old_topic = json['old']
        new_topic = json['new']

        sigma.relabel_topic(user, map_id, old, new)
        return jsonify(status='Relabel OK')
    except Exception as e:
        return jsonify(status='Relabel ERROR: ' + str(e))


@app.route('/fetchsearchdata', methods=['POST'])
@login_required
def fetch_searchdata():
    user = session['user']

    try:
        searchdata = sigma.get_searchdata(user)
        links = sigma.get_links(user)
        return jsonify(status='Search OK', searchdata=searchdata, linksdata=links)
    except Exception as e:
        return jsonify(status='Search ERROR:' + str(e))


@app.route('/tags', methods=['GET'])
@login_required
def get_tags():
    user = session['user']
    try:
        tags = sigma.get_tags(user)
        return jsonify(status='Tags OK', tags=tags)
    except Exception as e:
        return jsonify(status='Tags ERROR: ' + str(e))


@app.route('/deletelink', methods=['POST'])
@login_required
def delete_link():
    """
        Deletes a link from a a map, at a given subtopic node.
    """

    user = session['user']
    json = request.get_json()

    try:
        map_id = json.get('map_id', None)
        subtopic = json['subtopic']
        url = json['url']

        sigma.delete_link(user, map_id, subtopic, url)
        return jsonify(status='Delete OK')
    except Exception as e:
        return jsonify(status='Delete ERROR: ' + str(e))


@app.route('/fetchtitle', methods=['POST'])
@login_required
def fetch_title():
    """ 
        time.clock() - returns a floating point number of time since epoch
                    in seconds. Accuracy in microseconds.  -- Jonas """
    try:
        now = time.time()
        elapsed = now - session['last_request']

        if elapsed <= 2: 
            return jsonify(title="Too fast!")
        
        url = request.form.get('url', None)
        title = sigma.fetch_title(url)
        session['last_request'] = time.time()

        return jsonify(status="Title OK", title=title)

    except Exception as e:
        return jsonify(status="Title ERROR: " + str(e))


@app.route('/fetchmeta', methods=['POST'])
#@login_required
def fetch_meta():
    """ 
        Returns a filtered set of meta data about a given url.
        I.e:
            {
                meta: {
                    title: "A fish flying to the moon",
                    domain: "fishcanfly.com",
                    favicon: "https://fishcanfly.com/favicon.ico",
        
                    topics: {
                        cls1: {
                                Fish: 0.99999,
                                moon: 0.00001
                             },
                        success: True,
                        errorMessage: '',
                        version: '1.01',
                        textCoverage: 0.441786,
                        statusCode: 2000
                    }   
                }
            }                            -- Robin """
    try:
        now = time.time()
        elapsed = now - session['last_request']

        if elapsed <= 2: 
            return jsonify(status="Too fast!")

        session['last_request'] = time.time()
        url = request.form.get('url', None)
        filters = request.form.get('filter', None)
        # Not implemented filters yet. It dumps everything we got.
        meta = sigma.fetch_meta(url)
        # This will build a json response based on all the 
        # attributes in the LinkMeta object.
        return jsonify(status="Fetchmeta OK", meta=meta.__dict__)

    except Exception as e:
        return jsonify(status="Fetchmeta ERROR: " + str(e))


@app.route('/fetchlinks', methods=['GET'])
@login_required
def fetch_links():
    user = session['user']
    try:
        links = sigma.get_links(user)
        return jsonify(status='Links OK', links=links)
    except Exception as e:
        return jsonify(status='Links ERROR: ' + str(e))

# --------------------------------------------------------------------------- #
# ------------------------------- LAST ROUTE -------------------------------- #
###############################################################################


if __name__ == '__main__':
    import webbrowser # Webbrowser makes you able to open browser with specified url.
    webbrowser.open("http://localhost:5000")
    app.run(debug=True)

# EOF