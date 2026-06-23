from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

import os

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key"
)

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "1234"
)

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///players.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# UPLOAD FOLDER
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# MODELS

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))
    role = db.Column(db.String(50))
    dob = db.Column(db.Date)
    image = db.Column(db.String(200))

    stats = db.relationship(
        "Stat",
        backref="player",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Stat.created_at"
    )


class Stat(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    player_id = db.Column(
        db.Integer,
        db.ForeignKey("player.id"),
        nullable=False
    )

    heart_rate = db.Column(db.Integer)
    stress = db.Column(db.Integer)
    fatigue = db.Column(db.Integer)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# HOME PAGE

@app.route("/")
def home():

    if not session.get("logged_in"):
        return redirect("/login")

    players = Player.query.all()

    return render_template(
        "index.html",
        players=players
    )


# ADD PLAYER

@app.route("/add", methods=["POST"])
def add_player():

    if not session.get("logged_in"):
        return redirect("/login")

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")

    new_player = Player(
        name=f"{first_name} {last_name}",
        role=request.form.get("role"),
        dob=None,
        image=""
    )

    db.session.add(new_player)
    db.session.commit()

    return redirect("/")


# DELETE PLAYER

@app.route("/delete/<int:player_id>", methods=["POST"])
def delete_player(player_id):

    if not session.get("logged_in"):
        return redirect("/login")

    player = Player.query.get_or_404(player_id)

    if player.image:

        image_path = os.path.join(
            UPLOAD_FOLDER,
            player.image
        )

        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(player)
    db.session.commit()

    return redirect("/")


# LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

            session["logged_in"] = True

            return redirect("/")

        else:

            return render_template(
                "login.html",
                error="Invalid username or password"
            )

    return render_template("login.html")


# LOGOUT

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# PLAYER PAGE

@app.route("/player/<int:player_id>", methods=["GET", "POST"])
def player_page(player_id):

    if not session.get("logged_in"):
        return redirect("/login")

    player = Player.query.get_or_404(player_id)

    if request.method == "POST":

        # DOB
        dob_value = request.form.get("dob")

        if dob_value:

            player.dob = datetime.strptime(
                dob_value,
                "%Y-%m-%d"
            ).date()

        # IMAGE
        file = request.files.get("image")

        if file and file.filename != "":

            filename = f"{player.id}_{secure_filename(file.filename)}"

            file.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )
            )

            if player.image:

                old_image_path = os.path.join(
                    UPLOAD_FOLDER,
                    player.image
                )

                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
                    
            player.image = filename

        # NEW STAT ENTRY
        heart_rate = request.form.get("heart_rate")
        stress = request.form.get("stress")
        fatigue = request.form.get("fatigue")

        if heart_rate and stress and fatigue:

            new_stat = Stat(
                player_id=player.id,
                heart_rate=int(heart_rate),
                stress=int(stress),
                fatigue=int(fatigue)
            )

            db.session.add(new_stat)

        db.session.commit()

        return redirect(f"/player/{player.id}")

    # GRAPH DATA
    heart_rates = []
    dates = []

    for stat in player.stats:

        heart_rates.append(stat.heart_rate)

        dates.append(
            stat.created_at.strftime("%m/%d %I:%M %p")
        )

    return render_template(
        "player.html",
        player=player,
        heart_rates=heart_rates,
        dates=dates
    )


# UPDATE CURRENT STATS

@app.route("/update_stats/<int:stat_id>", methods=["POST"])
def update_stats(stat_id):

    if not session.get("logged_in"):
        return redirect("/login")

    stat = Stat.query.get_or_404(stat_id)

    stat.heart_rate = int(
        request.form.get("heart_rate")
    )

    stat.stress = int(
        request.form.get("stress")
    )

    stat.fatigue = int(
        request.form.get("fatigue")
    )

    db.session.commit()

    return redirect(f"/player/{stat.player_id}")


# DELETE STAT ENTRY

@app.route("/delete_stat/<int:stat_id>", methods=["POST"])
def delete_stat(stat_id):

    if not session.get("logged_in"):
        return redirect("/login")

    stat = Stat.query.get_or_404(stat_id)

    player_id = stat.player_id

    db.session.delete(stat)
    db.session.commit()

    return redirect(f"/player/{player_id}")


# DELETE PLAYER IMAGE

@app.route("/delete_image/<int:player_id>", methods=["POST"])
def delete_image(player_id):

    if not session.get("logged_in"):
        return redirect("/login")

    player = Player.query.get_or_404(player_id)

    if player.image:

        image_path = os.path.join(
            UPLOAD_FOLDER,
            player.image
        )

        if os.path.exists(image_path):
            os.remove(image_path)

        player.image = ""

    db.session.commit()

    return redirect(f"/player/{player.id}")


# RUN APP

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run()