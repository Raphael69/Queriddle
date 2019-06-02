from sqlalchemy import *
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker
import hashlib
import datetime
import os.path

engine = create_engine('sqlite:///base.db', echo=True)
Base = declarative_base()


def hasher(mystring):
    hash_object = hashlib.md5(mystring.encode())
    return hash_object.hexdigest()


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    username = Column(String, primary_key=True)
    email = Column(String)

    password = Column(String)
    status = Column(String)

    def __init__(self, email="", username="", password="", status=""):
        self.email = email
        self.username = username
        self.password = hasher(password)
        self.status = status


class Matiere(Base):
    __tablename__ = "matieres"

    nomMat = Column(String, primary_key=True)
    annee = Column(Integer)
    score = Column(Integer)

    def __init__(self, nomMat, annee):
        self.nomMat = nomMat
        self.score = 0
        self.annee = annee


class Tchat(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    contenu = Column(String)
    score = Column(Integer)
    refere = Column(Integer)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    type = Column(String)
    username = Column(Integer, ForeignKey("utilisateurs.username"))
    nomMat = Column(String, ForeignKey("matieres.nomMat"))

    user_rel = relationship("Utilisateur", foreign_keys=[username])
    mat_rel = relationship("Matiere", foreign_keys=[nomMat])

    def __init__(self, contenu, refere, username, idFichier, nomMat, type, score=0):
        self.contenu = contenu
        self.score = score
        self.refere = refere
        self.username = username
        self.idFichier = idFichier
        self.nomMat = nomMat
        self.type = type


class Fichier(Base):
    __tablename__ = "fichiers"
    id = Column(Integer, primary_key=True)
    nomFichier = Column(String)
    contenu = Column(Binary)
    typeFichier = Column(String)

    nomMat = Column(String, ForeignKey("matieres.nomMat"))

    mat_rel = relationship("Matiere", foreign_keys=[nomMat])

    def __init__(self, nomFichier, contenu, typeFichier, nomMat):
        self.nomFichier = nomFichier
        self.contenu = contenu
        self.typeFichier = typeFichier
        self.nomMat = nomMat


class QuestionArchive(Base):
    __tablename__ = "questionsArchivees"
    id = Column(Integer, primary_key=True)
    contenu = Column(String)

    username = Column(Integer, ForeignKey("utilisateurs.username"))
    nomMat = Column(String, ForeignKey("matieres.nomMat"))
    idFichier = Column(Integer, ForeignKey("fichiers.id"))

    user_rel = relationship("Utilisateur", foreign_keys=[username])
    mat_rel = relationship("Matiere", foreign_keys=[nomMat])
    fich_rel = relationship("Fichier", foreign_keys=[idFichier])

    def __init__(self, contenu, username, nomMat, idFichier):
        self.contenu = contenu
        self.username = username
        self.nomMat = nomMat
        self.idFichier = idFichier


class Commentaire(Base):
    __tablename__ = "commentaires"
    id = Column(Integer, primary_key=True)
    contenu = Column(String)
    username = Column(Integer, ForeignKey("utilisateurs.username"))
    idQuestArch = Column(Integer, ForeignKey("questionsArchivees.id"))
    user_rel = relationship("Utilisateur", foreign_keys=[username])
    user_rel = relationship("QuestionArchive", foreign_keys=[idQuestArch])

    def __init__(self, contenu, username, idQuestArch):
        self.contenu = contenu
        self.username = username
        self.idQuestArch = idQuestArch


class RaphMail(Base):
    __tablename__ = "raphmails"
    # On met ça en primary pour être sur de chez sur
    # Que personne aura la même clé d'url
    key_email = Column(String, primary_key=True)
    email = Column(String)

    def __init__(self, key_email, email):
        self.key_email = key_email
        self.email = email

class Like(Base):
    __tablename__="likes"
    id = Column(Integer, primary_key=True)
    idMessage=Column(Integer ,ForeignKey("messages.id"))
    username=Column(String,ForeignKey("utilisateurs.username"))
    user_rel = relationship("Utilisateur", foreign_keys=[username])
    message_rel = relationship("Tchat", foreign_keys=[idMessage])
    def __init__(self, idMessage,username):
        self.idMessage=idMessage
        self.username=username

class Dislike(Base):
    __tablename__="dislikes"
    id = Column(Integer, primary_key=True)
    idMessage=Column(Integer ,ForeignKey("messages.id"))
    username=Column(String,ForeignKey("utilisateurs.username"))
    user_rel = relationship("Utilisateur", foreign_keys=[username])
    message_rel = relationship("Tchat", foreign_keys=[idMessage])
    def __init__(self, idMessage,username):
        self.idMessage=idMessage
        self.username=username

'''
les méthodes from_asset font 2 choses,
en cherchant dans le dossier asset, où se trouvent les ressources, on :
1- Créé toutes les matieres ou fichiers associés
2- on renvoie un json des matieres par années 
'''
def db_from_asset():
    Session = sessionmaker(bind=engine)
    annees = os.listdir("static/asset")
    for annee in annees:
        matieres = os.listdir(os.path.join(os.getcwd(),"static/asset", annee))
        for matiere in matieres:
            new_matiere = Matiere(nomMat=matiere, annee=annee)
            session.add(new_matiere)
            fichiers = os.listdir(os.path.join(os.getcwd(),"static/asset", annee, matiere))
            for fichier in fichiers:
                new_fichier = Fichier(nomFichier=fichier, contenu=b'', typeFichier='pdf', nomMat=matiere)
                session.add(new_fichier)
    session.commit()

# create tables
Base.metadata.create_all(engine)
if __name__ == '__main__':
    if os.path.isfile("base.db"):
        os.remove("base.db")
        # create tables
        Base.metadata.create_all(engine) ## TODO peut inclure des erreurs

    # create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    user = Utilisateur(username="Raphael", password="Monin", email="raphael.monin@insa-lyon.fr", status="administrateur")
    session.add(user)
    user = Utilisateur(username="Marlon-Bradley", password="Paniah", email="to complete", status="utilisateur")
    session.add(user)
    user = Utilisateur(username="Maxime", password="Bernard", email="to complete", status="utilisateur")
    session.add(user)
    user = Utilisateur(username="Tom", password="Ltr", email="to complete", status="utilisateur")  # j'ai changé mon mdp batar
    session.add(user)
    user = Utilisateur(username="Basile", password="Deneire", email="to complete", status="utilisateur")
    session.add(user)
    db_from_asset()

    # commit the record the database
    session.commit()
