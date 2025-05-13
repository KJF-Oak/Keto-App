from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import json
import os

app = Flask(__name__, static_folder="static")

# Load base food data from Excel
excel_file = pd.ExcelFile("Food Calculator.xlsx")
database_df = excel_file.parse("DATABASE")
food_df = database_df.dropna(subset=["Item", "% PRT", "%FAT", "% CHO"])
food_df = food_df.rename(columns={"% PRT": "Protein", "%FAT": "Fat", "% CHO": "Carbs"})

# Load custom foods from JSON (if it exists)
CUSTOM_FOODS_FILE = "custom_foods.json"
if os.path.exists(CUSTOM_FOODS_FILE):
    with open(CUSTOM_FOODS_FILE, "r") as f:
        custom_foods = pd.DataFrame(json.load(f))
else:
    custom_foods = pd.DataFrame(columns=["Item", "Protein", "Fat", "Carbs"])

# Combine food data
all_foods_df = pd.concat([food_df, custom_foods], ignore_index=True)

# Saved meals file
MEALS_FILE = "saved_meals.json"
if not os.path.exists(MEALS_FILE):
    with open(MEALS_FILE, "w") as f:
        json.dump({}, f)

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/food-list", methods=["GET"])
def get_food_list():
    try:
        return jsonify(all_foods_df[["Item", "Protein", "Fat", "Carbs"]].dropna().to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add-food", methods=["POST"])
def add_food():
    try:
        new_food = request.get_json()
        required_fields = {"Item", "Protein", "Fat", "Carbs"}
        if not required_fields.issubset(new_food):
            return jsonify({"error": "Missing fields"}), 400

        existing = []
        if os.path.exists(CUSTOM_FOODS_FILE):
            with open(CUSTOM_FOODS_FILE, "r") as f:
                existing = json.load(f)

        existing.append(new_food)

        with open(CUSTOM_FOODS_FILE, "w") as f:
            json.dump(existing, f, indent=2)

        return jsonify({"success": True, "added": new_food})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/save-meal", methods=["POST"])
def save_meal():
    try:
        meal = request.get_json()
        name = meal.get("name")
        if not name or "rows" not in meal or "targetRatio" not in meal:
            return jsonify({"error": "Invalid meal data"}), 400

        with open(MEALS_FILE, "r") as f:
            meals = json.load(f)

        meals[name] = meal

        with open(MEALS_FILE, "w") as f:
            json.dump(meals, f, indent=2)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete-meal/<name>", methods=["DELETE"])
def delete_meal(name):
    try:
        with open(MEALS_FILE, "r") as f:
            meals = json.load(f)
        if name not in meals:
            return jsonify({"error": "Meal not found"}), 404

        del meals[name]

        with open(MEALS_FILE, "w") as f:
            json.dump(meals, f, indent=2)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/meals", methods=["GET"])
def get_meal_names():
    try:
        with open(MEALS_FILE, "r") as f:
            meals = json.load(f)
        return jsonify(sorted(meals.keys()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/meal/<name>", methods=["GET"])
def get_meal(name):
    try:
        with open(MEALS_FILE, "r") as f:
            meals = json.load(f)
        if name not in meals:
            return jsonify({"error": "Meal not found"}), 404
        return jsonify(meals[name])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
