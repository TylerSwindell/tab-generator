from flask import Flask, request, render_template, send_file
import os
from reportlab.pdfgen import canvas

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    margin_left = float(request.form.get("margin_left", 0.5)) * 72
    margin_right = float(request.form.get("margin_right", 0.5)) * 72
    num_columns = int(request.form.get("num_columns", 3))

    # Save uploaded file
    file = request.files["text_file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Generate PDF
    output_path = os.path.join(UPLOAD_FOLDER, "Tabbed_Output.pdf")
    create_tabbed_pdf(margin_left, margin_right, num_columns, file_path, output_path)

    return send_file(output_path, as_attachment=True)


def create_tabbed_pdf(
    margin_left, margin_right, num_columns, txt_file_path, output_path
):
    page_width = 11 * 72
    page_height = 9 * 72
    tab_height = 0.5 * 72
    usable_width = page_width - margin_left - margin_right
    column_width = usable_width / num_columns

    with open(txt_file_path, "r") as file:
        lines = [line.strip() for line in file if line.strip()]

    # Add blank tabs if the number of lines is less than the number of columns
    while len(lines) % num_columns != 0:
        lines.append("")  # Add blank tab

    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

    column_counter = 0

    for line in lines:
        column_x = margin_left + (column_counter % num_columns) * column_width
        column_y = page_height - tab_height / 2
        text_x = column_x + column_width / 2
        text_y = column_y

        c.drawCentredString(text_x, text_y, line)
        column_counter += 1
        c.showPage()

    c.save()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
