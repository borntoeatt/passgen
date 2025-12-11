from flask import Flask, request, jsonify
from password_generator import generate_password  # import from above

app = Flask(__name__)

@app.route("/generate", methods=["GET"])
def api_generate():
    length = int(request.args.get("length", 16))
    
    use_uppercase = request.args.get("uppercase", "true").lower() == "true"
    use_numbers = request.args.get("numbers", "true").lower() == "true"
    use_special = request.args.get("special", "true").lower() == "true"

    try:
        password = generate_password(
            length,
            use_uppercase,
            use_numbers,
            use_special
        )
        return jsonify({"password": password})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
