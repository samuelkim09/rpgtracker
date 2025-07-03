from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO
import sqlite3

app = Flask(__name__)
app.secret_key = "secret"
socketio = SocketIO(app)

GM_PASSWORD = "admin123"
DB_PATH = "db.sqlite3"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Initialisation DB
with get_db() as db:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, is_gm INTEGER DEFAULT 0,
        race TEXT, age INTEGER, poids REAL, niveau INTEGER, langues TEXT,
        force INTEGER, dexterite INTEGER, constitution INTEGER,
        intelligence INTEGER, sagesse INTEGER, charisme INTEGER,
        pv_actuels INTEGER, pv_max INTEGER,
        or_total INTEGER, argent_total INTEGER, platine_total INTEGER,
        xp INTEGER, histoire TEXT, bonus TEXT, talents TEXT, inventaire TEXT
    );
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, description TEXT, value_or INTEGER,
        effect_type TEXT, effect_stat TEXT, effect_value INTEGER,
        in_shop INTEGER DEFAULT 0, owner_id INTEGER
    );
    """)
    db.commit()


@app.route("/edit_player/<int:player_id>", methods=["GET", "POST"])
def edit_player(player_id):
    if "name" not in session:
        return redirect("/")

    with get_db() as db:
        gm = db.execute("SELECT * FROM players WHERE name=?",
                        (session["name"], )).fetchone()
        if not gm or not gm["is_gm"]:
            return "Accès refusé"

        if request.method == "POST":
            data = request.form
            db.execute(
                """
                UPDATE players SET
                    name=?, race=?, age=?, poids=?, niveau=?, langues=?,
                    force=?, dexterite=?, constitution=?, intelligence=?, sagesse=?, charisme=?,
                    pv_actuels=?, pv_max=?, or_total=?, argent_total=?, platine_total=?,
                    xp=?, histoire=?, bonus=?, talents=?
                WHERE id=?
            """, (data["name"], data["race"], data["age"], data["poids"],
                  data["niveau"], data["langues"], data["force"],
                  data["dexterite"], data["constitution"],
                  data["intelligence"], data["sagesse"], data["charisme"],
                  data["pv_actuels"], data["pv_max"], data["or_total"],
                  data["argent_total"], data["platine_total"], data["xp"],
                  data["histoire"], data["bonus"], data["talents"], player_id))
            db.commit()
            return redirect("/gm")

        all_players = db.execute("SELECT id, name FROM players").fetchall()
        items = db.execute("SELECT * FROM items WHERE owner_id=?",
                           (player_id, )).fetchall()
        player = db.execute("SELECT * FROM players WHERE id=?",
                            (player_id, )).fetchone()
        if not player:
            return "Joueur non trouvé", 404
        return render_template("edit_player.html",
                               p=player,
                               items=items,
                               all_players=all_players)


@app.route("/delete_item", methods=["POST"])
def delete_item():
    if "name" not in session:
        return redirect("/")

    with get_db() as db:
        gm = db.execute("SELECT * FROM players WHERE name=?",
                        (session["name"], )).fetchone()
        if not gm or not gm["is_gm"]:
            return "Accès refusé"

        item_id = request.form["item_id"]
        player_id = request.form["player_id"]
        db.execute("DELETE FROM items WHERE id=? AND owner_id=?",
                   (item_id, player_id))
        db.commit()
        return redirect(f"/edit_player/{player_id}")


@app.route("/add_item_to_player", methods=["POST"])
def add_item_to_player():
    if "name" not in session:
        return redirect("/")
    with get_db() as db:
        gm = db.execute("SELECT * FROM players WHERE name=?",
                        (session["name"], )).fetchone()
        if not gm or not gm["is_gm"]:
            return "Accès refusé"

        data = request.form
        db.execute(
            """
            INSERT INTO items (name, description, value_or, effect_type, effect_value, owner_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data["name"], data["description"], int(
                data["value_or"]), data["effect_type"],
              int(data["effect_value"]), int(data["player_id"])))
        db.commit()
        return redirect(f"/edit_player/{data['player_id']}")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        is_gm = "is_gm" in request.form
        if is_gm and request.form.get("password") != GM_PASSWORD:
            return "Mot de passe incorrect"

        with get_db() as db:
            user = db.execute("SELECT * FROM players WHERE name=?",
                              (name, )).fetchone()
            if not user:
                db.execute(
                    """
                    INSERT INTO players (name, is_gm, race, age, poids, niveau, langues,
                        force, dexterite, constitution, intelligence, sagesse, charisme,
                        pv_actuels, pv_max, or_total, argent_total, platine_total, xp,
                        histoire, bonus, talents, inventaire)
                    VALUES (?, ?, '', 20, 60, 1, '', 10,10,10,10,10,10,
                        10, 10, 50, 100, 2, 0, '', '', '{}', '{}')
                """, (name, int(is_gm)))
                db.commit()
            session["name"] = name
        return redirect("/gm" if is_gm else "/fiche")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/fiche")
def fiche():
    if "name" not in session:
        return redirect("/")
    with get_db() as db:
        p = db.execute("SELECT * FROM players WHERE name=?",
                       (session["name"], )).fetchone()
        items = db.execute("SELECT * FROM items WHERE owner_id=?",
                           (p["id"], )).fetchall()
        return render_template("player_home.html", p=p, items=items)


@app.route("/gm")
def gm():
    if "name" not in session:
        return redirect("/")
    with get_db() as db:
        gm = db.execute("SELECT * FROM players WHERE name=?",
                        (session["name"], )).fetchone()
        if not gm["is_gm"]:
            return "Accès interdit"
        players = db.execute("SELECT * FROM players WHERE is_gm=0").fetchall()
        items = db.execute("SELECT * FROM items").fetchall()
        return render_template("gm_panel.html", players=players, items=items)


@app.route("/create_item", methods=["POST"])
def create_item():
    data = request.json
    with get_db() as db:
        db.execute(
            """
            INSERT INTO items (name, description, value_or,
                effect_type, effect_stat, effect_value, in_shop)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data["name"], data["description"], data["value_or"],
              data["effect_type"], data["effect_stat"], data["effect_value"],
              int(data.get("in_shop", True))))
        db.commit()
    socketio.emit("items_updated")
    return jsonify(success=True)


@app.route("/toggle_shop")
def toggle_shop():
    socketio.emit("shop_toggle")
    return jsonify(success=True)


@app.route("/give_item", methods=["POST"])
def give_item():
    data = request.json
    item_id = data["item_id"]
    player_id = data["player_id"]
    with get_db() as db:
        db.execute("UPDATE items SET owner_id=?, in_shop=0 WHERE id=?",
                   (player_id, item_id))
        db.commit()
    socketio.emit("items_updated")
    return jsonify(success=True)


@app.route("/shop")
def shop():
    if "name" not in session:
        return redirect("/")
    with get_db() as db:
        p = db.execute("SELECT * FROM players WHERE name=?",
                       (session["name"], )).fetchone()
        items = db.execute(
            "SELECT * FROM items WHERE in_shop=1 AND owner_id IS NULL"
        ).fetchall()
        return render_template("shop.html", items=items, p=p)


@app.route("/buy_item", methods=["POST"])
def buy_item():
    data = request.json
    item_id = data["item_id"]
    currency = data["currency"]
    player_name = session["name"]
    with get_db() as db:
        p = db.execute("SELECT * FROM players WHERE name=?",
                       (player_name, )).fetchone()
        item = db.execute("SELECT * FROM items WHERE id=?",
                          (item_id, )).fetchone()
        price = item["value_or"]
        success = False

        if currency == "or" and p["or_total"] >= price:
            db.execute(
                "UPDATE players SET or_total = or_total - ? WHERE id = ?",
                (price, p["id"]))
            success = True
        elif currency == "argent" and p["argent_total"] >= price * 10:
            db.execute(
                "UPDATE players SET argent_total = argent_total - ? WHERE id = ?",
                (price * 10, p["id"]))
            success = True
        elif currency == "platine" and p["platine_total"] >= price // 5:
            db.execute(
                "UPDATE players SET platine_total = platine_total - ? WHERE id = ?",
                (price // 5, p["id"]))
            success = True

        if success:
            db.execute("UPDATE items SET owner_id=?, in_shop=0 WHERE id=?",
                       (p["id"], item_id))
            db.commit()
            socketio.emit("items_updated")
            return jsonify(success=True)
        return jsonify(success=False, error="Fonds insuffisants")


@socketio.on("connect")
def on_connect():
    emit("items_updated")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=81, debug=True)
