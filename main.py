from flask import Flask, render_template, jsonify, request, url_for, redirect, flash
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, relationship
from openai import OpenAI
import os
import stripe
import secrets
import base64
from flask_cors import CORS
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy.sql import func
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, DateField, ValidationError
from wtforms.validators import DataRequired, EqualTo, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
logger = logging.getLogger(__name__)

load_dotenv(override=True)

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///business.db"
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")
db.init_app(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

def widget_key():
    return request.args.get('key') or get_remote_address()


api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")
stripe.api_key = os.getenv("STRIPE_SECRET")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

openai = OpenAI()
client = OpenAI(api_key=api_key)
conversation_history = []

#Flask login stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#end of login stuff 


#form class
class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    password_hash = PasswordField('Password', validators=[DataRequired(), EqualTo('password_hash2', message="Passwords must match")])
    password_hash2 = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField("Submit")
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField("Submit")
    
#end of forms

# @app.route("/payment", methods=['GET', 'POST'])
# def payment():
#     if request.method == "POST":
#         price_id = "price_1SIwsQ1DMC7Ht8eGlC0ghdAy"
        
#         price_obj = stripe.Price.retrieve(price_id)
#         checkout_session = stripe.checkout.Session.create(
#             line_items=[
#                 {
#                     'price' : price_id,
#                     'quantity' : 1
#                 }
#             ],
#             mode = 'payment',
#             success_url = url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
#             cancel_url = url_for('cancel', _external=True)
#         )
#         return redirect(checkout_session.url, code=303)
#     return render_template('payment.html')

def get_limit_for_widget():
    key = request.args.get('key')
    if not key:
        return "1 per day"  # default if no key

    widget = Widget.query.filter_by(public_key=key).first()
    if not widget:
        return "1 per day"

    # Define plan-based limits
    if widget.plan == "free":
        return "2 per day"
    elif widget.plan == "Pro":
        return "5 per day"
    elif widget.plan == "flex":
        return "500 per day"
    else:
        return "1 per day"


@app.route("/success", methods=['GET', 'POST'])
def success():
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    subscription_id = session.subscription  
    
    metadata = session.get("metadata", {})
    widget_id = metadata.get("widget_id")
    plan = metadata.get("plan")

    # Verify this payment belongs to the current user
    widget = Widget.query.filter_by(id=widget_id, user_id=current_user.id).first()
    if not widget:
        return "Invalid widget or access denied", 403

    # Update the widget's plan
    widget.plan = plan
    widget.subscription_id = subscription_id
    db.session.commit()
    
    if session.payment_status == 'paid':
        return f'Successfully paid, session id {session_id}'
    else:
        return redirect('cancel')
    
@app.route("/cancel", methods=['GET', 'POST'])
def cancel():
    return 'payment cancelled'


@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    widgets = current_user.widgets
    return render_template('dashboard.html', widgets=widgets)

@app.route("/choose-plan/<int:widget_id>", methods=['GET', 'POST'])
@login_required
def choose_plan(widget_id): 
    widget = Widget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()
    plans = [
        {
           "name": "Pro", 
           "price": "£5/month", 
           "desc": "600 chats/month",
           "price_id" : "price_1SJPwP1DMC7Ht8eGtIrJiLxx"
        },
        {
            "name": "Flex", 
            "price": "$10/month", 
            "desc": "1500 chats/month + priority support",
            "price_id" : "price_1SJPvq1DMC7Ht8eGrCOrcu9t"
        }
    ]
    return render_template('plan.html', widget=widget, plans=plans)

@app.route("/upgrade/<int:widget_id>", methods=['GET', 'POST'])
@login_required
def upgrade(widget_id): 
    plan = request.form.get("plan")
    price_id = request.form.get("price_id")
    widget = Widget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()
    
    if request.method == "POST":
        # price_id = "price_1SIwsQ1DMC7Ht8eGlC0ghdAy"
        
        price_obj = stripe.Price.retrieve(price_id)
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price' : price_id,
                    'quantity' : 1
                }
            ],
            mode = 'subscription',
            success_url = url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url = url_for('cancel', _external=True),
             metadata={
                "user_id": current_user.id,
                "widget_id": widget.id,
                "plan": plan
            }
        )
        return redirect(checkout_session.url, code=303)
    return "hello"


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    # Verify signature
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        logger.exception("Invalid payload")
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        logger.exception("Invalid signature")
        return "Invalid signature", 400

    # Idempotency / duplicate protection (optional)
    event_id = event.get("id")
    # You can store processed event_ids in DB to avoid re-processing (recommended for production)

    try:
        typ = event["type"]
        obj = event["data"]["object"]

        # subscription created/first payment succeeded
        if typ == "checkout.session.completed":
            # if using session metadata to link widget:
            widget_id = obj.get("metadata", {}).get("widget_id")
            plan = obj.get("metadata", {}).get("plan")
            subscription_id = obj.get("subscription")  # may be present
            if widget_id:
                widget = Widget.query.get(widget_id)
                if widget:
                    widget.plan = plan or widget.plan
                    if subscription_id:
                        widget.subscription_id = subscription_id
                    db.session.commit()

        # recurring invoice payment succeeded -> renewal happened
        elif typ == "invoice.payment_succeeded":
            subscription_id = obj.get("subscription")
            # map subscription -> widget
            widget = Widget.query.filter_by(subscription_id=subscription_id).first()
            

        # subscription cancelled (customer or Stripe)
        elif typ == "customer.subscription.deleted":
            subscription_id = obj.get("id")
            widget = Widget.query.filter_by(subscription_id=subscription_id).first()
            if widget:
                widget.plan = "free"
                widget.subscription_id = None
                db.session.commit()

        # payment failed (optional handling)
        elif typ == "invoice.payment_failed":
            subscription_id = obj.get("subscription")
            widget = Widget.query.filter_by(subscription_id=subscription_id).first()

        # add other events you care about...
    except Exception:
        logger.exception("Error handling webhook event")
        # Return 500 so Stripe retries the event later
        return "Server error", 500

    # Return 200 quickly to acknowledge receipt
    return "OK", 200

    



@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            #check and compare hash
            if check_password_hash(user.password_hash, form.password.data):
               login_user(user)     
               flash('login successful')
               return redirect(url_for('dashboard'))
            else:
                flash('wrong password, try again')
        else:
            flash('user does not exist!')
    return render_template('login.html', form=form)

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = UserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user == None:
            name = form.name.data
            username = form.username.data
            email = form.email.data
            password = form.password_hash.data
            confirm_password = form.password_hash2.data

            user = User(
                name = form.name.data,
                username = form.username.data,
                email = form.email.data,
                password = form.password_hash.data
                )
            print(name, username, email, password, confirm_password)
            db.session.add(user)
            db.session.commit()
            flash('user registered successfully')
        name = ''
        username = ''
        email = ''
        
    return render_template('register.html', form=form)

@app.route("/")
@login_required
def home():
    return render_template('home.html')

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    logout_user()
    flash('you have been logged out, bye!')
    return redirect(url_for('login'))


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
        email=query['email'],
        user_id=current_user.id
        )
    db.session.add(widget)
    db.session.commit()
    widget_key = widget.public_key
    script_url = f'<script src="{base_url}/widget.js" data-key="{widget_key}"></script>'
    return jsonify(
            {
                # "widget" : widget,
                "widget_key": widget_key,
                "script_url": script_url
            }
        )

@app.route("/chat", methods=['POST'])
@limiter.limit(get_limit_for_widget, key_func=widget_key)
def chat_data():
    key = request.args.get('key')
    query = request.get_json()
    query_q = query['question']
    
    widget = Widget.query.filter_by(public_key=key).first_or_404()
    
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
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    public_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: Widget.generate_key())
    plan: Mapped[str] = mapped_column(String(50), default="free")
    subscription_id: Mapped[str] = mapped_column(String(100), nullable=True)
    user = relationship("User", back_populates="widgets")
    @staticmethod
    def generate_key():
        # Generates something like wgt_Fz73JpA2n5YbC6qW1kZx0v
        return "wgt_" + secrets.token_urlsafe(16)

class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    date_added: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    password_hash: Mapped[str] = mapped_column("password", nullable=False)
    widgets = relationship("Widget", back_populates="user",  cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError("Password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
with app.app_context():
    db.create_all()