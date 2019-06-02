from flask import Flask, flash, redirect, render_template, request, session, abort, url_for, send_from_directory
from flask_mail import Mail, Message
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import os
import re
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from random import choice
from string import ascii_lowercase
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from tabledef import Utilisateur, RaphMail, Matiere, hasher, Tchat, Fichier, Like, Dislike
engine = create_engine('sqlite:///base.db', echo=True)

ALLOWED_EXTENSIONS = set(['pdf'])

app = Flask(__name__)
socketio = SocketIO(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

##Admin
class MyModel(ModelView):
    column_display_pk = True
    form_columns = ('username', 'password', 'email')

class MyAdminIndexView(AdminIndexView):
    def is_accessible(selfself):
        Session = sessionmaker(bind=engine)
        s = Session()
        statut = s.query(Utilisateur.status).filter(Utilisateur.username == session['username']).first()[0]
        return session.get('logged_in') and statut == 'administrateur'

db = SQLAlchemy(app)
admin = Admin(app, index_view=MyAdminIndexView())

admin.add_view(MyModel(Utilisateur, db.session))
admin.add_view(ModelView(RaphMail, db.session))
admin.add_view(ModelView(Matiere, db.session))
admin.add_view(ModelView(Tchat, db.session))
admin.add_view(ModelView(Fichier, db.session))
admin.add_view(ModelView(Like, db.session))
admin.add_view(ModelView(Dislike, db.session))

##Upload
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/upload/<string:anneeChoisi>/<string:matiereChoisi>/<string:sujetChoisi>/<string:username>', methods=['POST'])
def upload_file(anneeChoisi, matiereChoisi, sujetChoisi, username):
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(url_for('home'))
        file = request.files['file']
        name = username + ".pdf"
        if file.filename == '':
            flash('Aucun fichier sélectionné')
            return redirect(url_for('home'))
        if file and allowed_file(file.filename):
            file.save(os.path.join('static/upload/'+anneeChoisi+'/'+matiereChoisi+'/'+sujetChoisi, name))
            flash('Votre proposition de correction a été envoyé avec succès')
            return redirect(url_for('home'))

##Admin soft
@app.route('/as')
def manage_files():
    if not session.get('logged_in'):
        return redirect(url_for('do_admin_login'))
    Session = sessionmaker(bind=engine)
    s = Session()
    statut = s.query(Utilisateur.status).filter(Utilisateur.username == session['username']).first()[0]
    if statut != 'administrateur':
        return redirect(url_for('home'))
    return render_template('manage_files.html', myUsername=session['username'])



##Main
@app.route('/')
@app.route('/<string:anneeChoisi>/<string:matiereChoisi>/<string:sujetChoisi>')
def home(anneeChoisi="3TC", matiereChoisi="TSA", sujetChoisi="DS2016_s.pdf"):
    if not session.get('logged_in'):
        return redirect(url_for('do_admin_login'))
    else:
        lien = "/static/asset/" + anneeChoisi + "/" + matiereChoisi + "/" + sujetChoisi
        lien2 = "/static/asset/" + anneeChoisi + "/" + matiereChoisi + "/" + sujetChoisi[:-5] + "c.pdf"
        return render_template('ressources.html', myUsername=session['username'], lien=lien, lien2=lien2, anneeCh=anneeChoisi, matiereCh= matiereChoisi, sujetCh=sujetChoisi[:-6])

@app.route('/login', methods=['GET','POST'])
def do_admin_login():
    if request.method == 'POST':
        POST_USERNAME = str(request.form['username'])
        POST_PASSWORD = str(request.form['password'])
        password_hash=hasher(POST_PASSWORD)

        Session = sessionmaker(bind=engine)
        s = Session()
        query = s.query(Utilisateur).filter(Utilisateur.username.in_([POST_USERNAME]), Utilisateur.password.in_([password_hash]))
        result = query.first()
        if result:
            session['logged_in'] = True
            session['username'] = POST_USERNAME
        else:
            flash('Mot de passe incorrect !')
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/my_account')
def my_account():
    Session = sessionmaker(bind=engine)
    s = Session()
    query=s.query(Utilisateur).filter(Utilisateur.username == session['username'])[0]
    return render_template('my_account.html', myUsername = query.username, myStatus = query.status, myEmail = query.email)

@app.route('/create_account/<string:key>', methods=['GET','POST'])
def create_account(key):
    if request.method == 'POST':
        Session = sessionmaker(bind=engine)
        s = Session()
        #Check si l'username existe déjà
        query = s.query(Utilisateur.username).filter(Utilisateur.username.in_([request.form['username']]))
        print("Lllll", query.first())
        if query.first():
            print("LLLllllooooooo")
            flash("Ce nom d'utilisateur existe déjà !")
            return redirect(url_for('create_account', key=key))
        # On récupère l'adresse mail correspondante, qui doit forcement exister
        query = s.query(RaphMail.email).filter(RaphMail.key_email.in_([key]))
        user = Utilisateur(username=str(request.form['username']), password=str(request.form['password']), email=str(query.first()[0]), status="utilisateur")
        s.add(user)
        s.commit()
        return redirect(url_for('do_admin_login'))
    return render_template('create_account.html', key=key)

@app.route('/new_account', methods=['GET','POST'])
def new_account():
    if request.method == 'POST':
        #Check si l'email existe déjà
        Session = sessionmaker(bind=engine)
        s = Session()
        query = s.query(RaphMail.email).filter(RaphMail.email.in_([request.form['email']]))
        if query.first():
            flash("Cette adresse mail est déjà utilisé !")
            return redirect(url_for('new_account'))
        #Envoie l'email
        mail_settings = {
            "MAIL_SERVER": 'smtp.gmail.com',
            "MAIL_PORT": 465,
            "MAIL_USE_TLS": False,
            "MAIL_USE_SSL": True,
            "MAIL_USERNAME": "queriddle@gmail.com",
            "MAIL_PASSWORD": "Fullstack69!",
        }
        app.config.update(mail_settings)
        mail = Mail(app)
        key = "".join(choice(ascii_lowercase) for i in range(10))
        msg = Message(subject="Merci Marley !",
                      sender=app.config.get("MAIL_USERNAME"),
                      recipients=[request.form['email']],
                      body="Salut va sur ce lien pour creer ton compte : http://127.0.0.1:5000/create_account/"+key)
        mail.send(msg)
        # Stock les données
        user2 = RaphMail(key_email=str(key), email=str(request.form['email']))
        s.add(user2)
        s.commit()
        return render_template('login.html')
    return render_template('new_account.html')

@app.route("/logout")
def logout():
    session['logged_in'] = False
    session.pop('username', None)
    return redirect(url_for('home'))

def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')

@socketio.on('init_manage_files')
def handle_my_custom_event(msg, methods=['GET', 'POST']):
    annees = os.listdir("static/upload")
    for a in annees:
        if(a != ".DS_Store"):
            matieres = os.listdir("static/upload/"+a)
            sous_message = []
            for m in matieres:
                if(m != ".DS_Store"):
                    sous_message.append(m)
            message = { "annee": a , "matieres": sous_message}
            socketio.emit('les_annees', message)

@socketio.on('init_manage_files2')
def handle_my_custom_event(msg, methods=['GET', 'POST']):
    sujets = os.listdir("static/upload/"+msg['annee']+'/'+msg['matiere'])
    for s in sujets:
        if(s != ".DS_Store"):
            propositions = os.listdir("static/upload/"+msg['annee']+'/'+msg['matiere']+'/'+ s)
            if propositions:
                sous_message = []
                for p in propositions:
                    if(p != ".DS_Store"):
                        sous_message.append(p)
                message = {"annee": msg['annee'], "matiere": msg['matiere'], "sujet": s, "propositions": sous_message}
                print("LLL", message)
                socketio.emit('les_annees2', message)

@socketio.on('manage_file_suppression')
def handle_my_custom_event(msg, methods=['GET', 'POST']):
    os.remove(msg['lien'])

@socketio.on('manage_file_suppression')
def handle_my_custom_event(msg, methods=['GET', 'POST']):
    filename = msg['lien'].rsplit("/")
    new_filename = 'static/asset/'+filename[2]+'/'+filename[3]+'/'+filename[4]+'_c.pdf'
    os.rename(msg['lien'], new_filename)

@socketio.on('initChoixMat')
def handle_event(msg, methods=['GET', 'POST']):
    print("Hehehehehohohohoo")
    Session = sessionmaker(bind=engine)
    s = Session()
    query = s.query(Matiere.nomMat).filter(Matiere.annee == msg["annee"], Matiere.nomMat != msg['matiere'])
    matieres = []
    for q in query:
        matieres.append(q[0])
        print("Lalalalaaaaaaaaaa", q[0])
    socketio.emit('initChoixMatBack', matieres)

@socketio.on('init')
def handle_my_custom_event(msg, methods=['GET', 'POST']):
    #if msg['user'] != session['username']:
    #    return -1
    Session = sessionmaker(bind=engine)
    s = Session()
    print("LLLllllLE MESSAGE", msg)
    if (msg['choixChat'] == 'General'):
        print("Ici")
        query = s.query(Tchat)
    else:
        query = s.query(Tchat).filter(Tchat.type == 'Matiere', msg['matiere'] == Tchat.nomMat)
    message = []
    i = 0
    if(not(query.first())):
        socketio.emit('efface')
    for q in query:
        i = i + 1
        scoreLike = s.query(Like).filter(Like.idMessage == q.id).count()
        scoreDislike = s.query(Dislike).filter(Dislike.idMessage == q.id).count()
        if(i == 1):
            message = { "matiere": q.nomMat, "id": q.id, "username": q.username, "message": q.contenu, 'reference': q.refere, "scoreLike": scoreLike, "scoreDislike": scoreDislike, "init": "yes" }
        else:
            message = { "matiere": q.nomMat, "id": q.id, "username": q.username, "message": q.contenu, 'reference': q.refere, "scoreLike": scoreLike, "scoreDislike": scoreDislike, "init": "no" }
        socketio.emit('messageReception', message, callback=messageReceived)

@socketio.on('messageEmission')
def handle_my_custom_event(msg, methods=['GET', 'POST']):
    Session = sessionmaker(bind=engine)
    s = Session()
    print("LLLllLE MESSAGE", msg)
    new_message=Tchat(username = msg['username'], nomMat = msg['matiere'], refere = msg['reference'],contenu = msg["message"],idFichier = 0, type = msg['choixChat'])
    s.add(new_message)
    s.commit()
    query = s.query(func.max(Tchat.id)).first()
    updated_msg = {
        'id' : str(query[0]),
        'matiere' : msg['matiere'],
        'message': msg['message'],
        'username': msg['username'],
        'reference': msg['reference'],
        'scoreLike': 0,
        'scoreDislike': 0,
        'init': "no",
    }
    socketio.emit('messageReception', updated_msg, callback=messageReceived)
    print('Message reçu: ' + str(updated_msg))

@socketio.on('likeEmission')
def handle_my_custom(msg, methods=['GET', 'POST']):
    Session = sessionmaker(bind=engine)
    s = Session()
    redundancy = s.query(Like).filter(Like.idMessage == msg['id'], Like.username == msg['username']).first()
    if redundancy:
        return -1
    if(s.query(Dislike).filter(Dislike.idMessage == msg['id'], Dislike.username == msg['username']).delete()):
        scoreDislike = s.query(Dislike).filter(Dislike.idMessage == msg['id']).count()
        updated_msg = {
            'id': msg['id'],
            'scoreDislike': scoreDislike
        }
        socketio.emit('dislikeReception', updated_msg, callback=messageReceived);
    new_like = Like(username=msg['username'], idMessage=msg['id'])
    s.add(new_like)
    s.commit()
    scoreLike = s.query(Like).filter(Like.idMessage == msg['id']).count()
    updated_msg = {
        'id': msg['id'],
        'scoreLike': scoreLike
    }
    socketio.emit('likeReception', updated_msg, callback=messageReceived);

@socketio.on('dislikeEmission')
def handle_my_custom(msg, methods=['GET', 'POST']):
    Session = sessionmaker(bind=engine)
    s = Session()
    redundancy = s.query(Dislike).filter(Dislike.idMessage == msg['id'], Dislike.username == msg['username']).first()
    if redundancy:
        return -1
    if (s.query(Like).filter(Like.idMessage == msg['id'], Like.username == msg['username']).delete()):
        scoreLike = s.query(Like).filter(Like.idMessage == msg['id']).count()
        updated_msg = {
            'id': msg['id'],
            'scoreLike': scoreLike
        }
        socketio.emit('likeReception', updated_msg, callback=messageReceived);
    new_dislike = Dislike(username=msg['username'], idMessage=msg['id'])
    s.add(new_dislike)
    s.commit()
    scoreDislike = s.query(Dislike).filter(Dislike.idMessage == msg['id']).count()
    updated_msg = {
        'id': msg['id'],
        'scoreDislike': scoreDislike
    }
    socketio.emit('dislikeReception', updated_msg, callback=messageReceived);

@socketio.on('changeMat')
def handle_event(msg, methods=['GET', 'POST']):
    Session = sessionmaker(bind=engine)
    s = Session()
    print('received my event: ' + str(msg))
    query = s.query(Matiere.nomMat).filter(Matiere.annee == msg["annee"])
    matieres = []
    for q in query:
        matieres.append(q[0])
    socketio.emit('effChangeMat', matieres)

@socketio.on('changeFic')
def handle_event(msg, methods=['GET', 'POST']):
    Session = sessionmaker(bind=engine)
    s = Session()
    print('received my event: ' + str(msg))
    query = s.query(Fichier.nomFichier).filter(Fichier.nomMat == msg["matiere"])
    matieres = []
    for q in query:
        if(q[0][-5]=='s'):
            matieres.append(q[0])
            print("LLLLL", q[0])
    socketio.emit('effChangeFic', matieres)

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
