from flask import Flask, request, jsonify
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
    return app.send_static_file("index.html")

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

@app.route("/get-food-options", methods=["POST"])
def get_food_options():
    data = request.get_json()
    try:
        food_type = data.get("food_type", None)
        calories = float(data["calories"])
        meals_per_day = int(data["meals"])
        ratio = float(data["ratio"])

        kcal_per_meal = calories / meals_per_day
        kcal_unit = 22
        units_per_meal = kcal_per_meal / kcal_unit

        total_parts = ratio + 1 + 0.1
        fat_kcal = (ratio / total_parts) * kcal_per_meal
        protein_kcal = (1 / total_parts) * kcal_per_meal
        carbs_kcal = kcal_per_meal - (fat_kcal + protein_kcal)

        target_macros = {
            "Fat": round(fat_kcal / 9, 1),
            "Protein": round(protein_kcal / 4, 1),
            "Carbs": round(carbs_kcal / 4, 1)
        }

        filtered_df = all_foods_df
        if food_type:
            filtered_df = filtered_df[filtered_df["Type"].str.lower() == food_type.lower()] if "Type" in filtered_df else filtered_df

        food_options = filtered_df[["Item", "Protein", "Fat", "Carbs"]].to_dict(orient="records")

        return jsonify({
            "per_meal_targets": target_macros,
            "food_options": food_options[:50]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
