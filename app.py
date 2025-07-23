# app.py

from flask import Flask, render_template, request
import pandas as pd
from flask import make_response
from weasyprint import HTML

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_tos():
    # === Get general information ===
    course_code = request.form.get('course_code')
    units = request.form.get('units')
    course_title = request.form.get('course_title')
    time = request.form.get('time')
    course_year = request.form.get('course_year')
    days = request.form.get('days')
    semester = request.form.get('semester')
    exam_title = request.form.get('exam_title')
    instructor = request.form.get('instructor')
    instructor_designation = request.form.get('instructor_designation')
    noted_by = request.form.get('noted_by')
    noted_by_designation = request.form.get('noted_by_designation')
    total_items = int(request.form.get('total_items'))

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    from jinja2 import Template

    rendered_html = request.form.get('html')

    pdf = HTML(string=rendered_html).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=table_of_specifications.pdf'
    return response

    # === Get topic data ===
    topics = request.form.getlist('topic[]')
    hours = [float(h) for h in request.form.getlist('hours[]')]
    total_hours = sum(hours)

    # === Get selected domains and their weights ===
    domain_names = ["Remembering", "Understanding", "Applying", "Analyzing", "Evaluating", "Creating"]
    selected_domains = []
    domain_weights = {}

    for domain in domain_names:
        if request.form.get('percent_' + domain):
            percent = request.form.get('percent_' + domain)
            try:
                weight = float(percent)
                if weight > 0:
                    selected_domains.append(domain)
                    domain_weights[domain] = weight / 100.0
            except ValueError:
                continue

    if len(selected_domains) != 3:
        return "Error: You must select exactly 3 domains with valid percentages.", 400

    if round(sum(domain_weights.values()), 2) != 1.0:
        return "Error: Domain percentages must sum to 100%.", 400

    # === Step 1: Calculate raw item allocations per topic ===
    raw_topic_items = [(topic, h, (h / total_hours) * total_items) for topic, h in zip(topics, hours)]

    # === Step 2: Round down and collect remainders ===
    item_allocations = []
    remainders = []
    total_assigned = 0

    for topic, h, raw_items in raw_topic_items:
        base = int(raw_items)
        remainder = raw_items - base
        total_assigned += base
        item_allocations.append({'Topic': topic, 'Hours': h, 'Items': base, '_remainder': remainder})
    
    # === Step 3: Distribute remaining items ===
    remaining_items = total_items - total_assigned
    # Attach original index to preserve order
    for idx, item in enumerate(item_allocations):
        item['_index'] = idx

    # Sort by remainder to distribute remaining items
    sorted_remainders = sorted(item_allocations, key=lambda x: x['_remainder'], reverse=True)

    for i in range(remaining_items):
        sorted_remainders[i]['Items'] += 1

    # Remove temporary keys
    for item in item_allocations:
        del item['_remainder']
        del item['_index']

    # Restore original order
    item_allocations.sort(key=lambda x: topics.index(x['Topic']))

    # === Step 4: Distribute items across cognitive domains ===
    final_allocations = []
    for item in item_allocations:
        topic_items = item['Items']
        topic_data = {
            'Topic': item['Topic'],
            'Hours': item['Hours'],
            'Items': topic_items
        }

        remaining = topic_items
        # Allocate to all but last
        for domain in selected_domains[:-1]:
            count = int(round(topic_items * domain_weights[domain]))
            topic_data[domain] = count
            remaining -= count
        # Assign remaining to last domain
        topic_data[selected_domains[-1]] = remaining

        # Fill 0 for unselected domains
        for d in domain_names:
            if d not in topic_data:
                topic_data[d] = 0

        final_allocations.append(topic_data)

    # === Step 5: Create DataFrame and calculate totals ===
    df = pd.DataFrame(final_allocations)
    df['% of Items'] = ((df['Items'] / total_items) * 100).round().astype(int)

    totals = pd.DataFrame(df.drop(columns=['Topic']).sum()).T
    totals['Topic'] = 'TOTAL'
    df = pd.concat([df, totals], ignore_index=True)
    df_records = df.to_dict(orient='records')

    return render_template('result.html',
                           df=df_records,
                           course_code=course_code,
                           units=units,
                           course_title=course_title,
                           time=time,
                           course_year=course_year,
                           days=days,
                           instructor=instructor,
                           noted_by=noted_by,
                           instructor_designation = instructor_designation,
                           noted_by_designation = noted_by_designation,
                           total_items=total_items,
                           selected_domains=selected_domains,
                           domain_weights=domain_weights,
                           semester=semester,
                           exam_title=exam_title)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)