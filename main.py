from flask import Flask, render_template, jsonify, request, url_for, redirect
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI
import os
import base64
from flask_cors import CORS
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy.sql import func
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, DateField
from wtforms.validators import DataRequired
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
# login_manager = LoginManager()

load_dotenv(override=True)

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///business.db"
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")
db.init_app(app)


api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")

openai = OpenAI()
client = OpenAI(api_key=api_key)
conversation_history = []

#form class
class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    # date = DateField('Date Added', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField("Submit")
    
#end of forms

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = UserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user == None:
            name = form.name.data
            username = form.username.data
            email = form.email.data
            password = form.password.data
            # name = form.name.data
            user= User(
                name = form.name.data,
                username = form.username.data,
                email = form.email.data,
                password = form.password.data
                )
            print(name, username, email, password)
            db.session.add(user)
            db.session.commit()
        name = ''
        username = ''
        email = ''
        password = ''
    return render_template('register.html', form=form)

@app.route("/")
def home():
    return render_template('home.html')


@app.route("/save-data", methods=['POST'])
def save_data():
    query = request.get_json()
    name = query['name']
    summary = query['summary']
    email = query['email']
    data = {
            "name": name,
            "summary": summary,
            "email": email
        }
    widget = Widget(
        username=query['name'],
        summary=query['summary'],
        email=query['email']
        )
    db.session.add(widget)
    db.session.commit()
    widget_id = widget.id
    script_url = f'<script src="{base_url}/widget.js" data-id="{widget_id}"></script>'
    return jsonify(
            {
                # "widget" : widget,
                "widget_id": widget_id,
                "script_url": script_url
            }
        )

@app.route("/chat", methods=['POST'])
def chat_data():
    id = request.args.get('id', type=int)
    query = request.get_json()
    query_q = query['question']
    
    widget = db.get_or_404(Widget, id)
    
    system_prompt = f"""
        You are now acting as the owner of this business. 
        name of business is {widget.username}
        You must ONLY use the following summary to answer questions:

        {widget.summary}

        Rules:
        - If the answer is found in the summary, respond as if you are the business.
        - If the answer is NOT in the summary, say exactly:
        "I don’t know. Please leave a message at {widget.email}."
        - Do not make up or guess any information not in the summary.
        - Always stay in character as the business.
    """   
   
    if query_q:
        conversation_history = [{'role':'system', 'content': system_prompt}]
        conversation_history.append({'role':'user', 'content': query_q})
        response = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=conversation_history,
            temperature=0
        )

        reply = response.choices[0].message.content
        # print(response.choices[0].message.content)
        conversation_history.append({'role':'assistant', 'content': response.choices[0].message.content})
        # print(query)
        data = {
            "query": query_q,
            "answer": reply
        }
    return jsonify(data)
    
@app.route("/widget.js")
def widget():
    return app.send_static_file("widget.js")



class Widget(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    date_added: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    password: Mapped[str] = mapped_column(nullable=False)
   
    
# with app.app_context():
#     db.create_all()