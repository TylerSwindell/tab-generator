from flask import Flask, request, render_template, send_file, jsonify
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib.utils import simpleSplit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configure SQLAlchemy database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tabs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Define database model for tab data
class TabList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_ip = db.Column(db.String(50), nullable=False)
    tab_text = db.Column(db.Text, nullable=False)
    margin_left = db.Column(db.Float, nullable=False)
    margin_right = db.Column(db.Float, nullable=False)
    num_columns = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TabList {self.id} {self.user_ip}>"


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.before_request
def create_tables():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    margin_left = float(request.form.get("margin_left", 0.5)) * 72
    margin_right = float(request.form.get("margin_right", 0.5)) * 72
    num_columns = int(request.form.get("num_columns", 5))
    fill_blanks = bool(request.form.get("fill_blanks"))

    print(fill_blanks)
    # Save uploaded file
    file = request.files["text_file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Read lines from file
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    if fill_blanks:
        # Add blank tabs if necessary
        while len(lines) % num_columns != 0:
            lines.append("")  # Add blank tab

    # Save data to the database
    user_ip = request.remote_addr
    tab_text = "\n".join(lines)
    new_tab_list = TabList(
        user_ip=user_ip,
        tab_text=tab_text,
        margin_left=margin_left / 72,  # Convert back to inches for storage
        margin_right=margin_right / 72,  # Convert back to inches for storage
        num_columns=num_columns,
    )
    db.session.add(new_tab_list)
    db.session.commit()

    # Generate PDF
    output_path = os.path.join(UPLOAD_FOLDER, "Tabbed_Output.pdf")
    if not create_tabbed_pdf(
        margin_left, margin_right, num_columns, lines, output_path
    ):
        return (
            jsonify(
                {
                    "error": "Some text is too long to fit in the tabs. Please use shorter text."
                }
            ),
            400,
        )

    return send_file(output_path, as_attachment=True)


@app.route("/view_tabs")
def view_tabs():
    tabs = TabList.query.all()  # Retrieve all entries from the TabList table
    results = [
        {
            "id": tab.id,
            "user_ip": tab.user_ip,
            "tab_text": tab.tab_text,
            "margin_left": tab.margin_left,
            "margin_right": tab.margin_right,
            "num_columns": tab.num_columns,
            "created_at": tab.created_at,
        }
        for tab in tabs
    ]
    return {"tabs": results}  # Return data as a JSON response


def create_tabbed_pdf(margin_left, margin_right, num_columns, lines, output_path):
    page_width = 11 * 72
    page_height = 9 * 72
    tab_height = 0.5 * 72
    max_text_height = 0.45 * 72  # Maximum height for text in the tab section
    usable_width = page_width - margin_left - margin_right
    column_width = usable_width / num_columns

    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

    column_counter = 0
    min_font_size = 9  # Minimum font size allowed

    for line in lines:
        column_x = margin_left + (column_counter % num_columns) * column_width
        column_y = page_height - tab_height / 2

        font_size = 12  # Start with a default font size
        text_fits = False

        # Attempt to fit the text by adjusting the font size and adding line breaks
        while font_size >= min_font_size:
            c.setFont("Helvetica", font_size)
            wrapped_text = simpleSplit(
                line, "Helvetica", font_size, column_width - 10
            )  # 10 pts padding

            # Check if all lines fit within the maximum text height
            if (
                len(wrapped_text) * font_size <= max_text_height
            ):  # Ensure text stays within bounds
                text_fits = True
                break

            font_size -= 1

        if not text_fits:
            return False  # Text does not fit, cancel PDF creation

        # Draw the text in the center of the column
        start_y = column_y + max_text_height / 2 - (len(wrapped_text) * font_size) / 2
        for i, text in enumerate(wrapped_text):
            c.drawCentredString(
                column_x + column_width / 2, start_y - i * font_size, text
            )

        column_counter += 1
        c.showPage()

    c.save()
    return True


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
