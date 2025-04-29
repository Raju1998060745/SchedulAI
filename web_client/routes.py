from flask import Blueprint, render_template, request, redirect, url_for

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')

@main.route('/plan', methods=['POST'])
def plan_goal():
    goal_text = request.form.get('goal')
    # TODO: Send this goal to ADK Agent (next steps)
    return redirect(url_for('main.home'))
