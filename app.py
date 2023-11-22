import datetime
import os
import random
import requests
from flask import Flask, request, render_template, jsonify, redirect, url_for
import threading
from loguru import logger
import json
import csv
app = Flask(__name__)
current_question_index = 0
global questions
global answeredQuestions
answeredQuestions = []


@app.route("/api/validateinput", methods=["POST"])
def showQuestions():
    data = request.get_json()
    logger.logger.info(f"I got the userdata from here: {data}")
    global user
    user = {}
    subject = None
    random_options = None
    random_questions = None
    on_spot_assessment = None
    grade = None
    if not request.is_json:
        return jsonify(error="Request data must be in JSON format"), 400
    else:
        if 'subject' in data:
            subject = data['subject']
            if not isinstance(subject, str):
                return jsonify(error=f"Invalid 'subject' type. Should be a string"), 400
        if 'random_options' in data:
            random_options = data['random_options']
            if not isinstance(random_options, bool):
                return jsonify(error=f"Invalid 'random_options' type. Should be a boolean"), 400
        if 'random_questions' in data:
            random_questions = data['random_questions']
            if not isinstance(random_questions, bool):
                return jsonify(error=f"Invalid 'random_questions' type. Should be a boolean"), 400
        if 'spot_assess' in data:
            on_spot_assessment = data['spot_assess']
            if not isinstance(on_spot_assessment, bool):
                return jsonify(error=f"Invalid 'spot_assess' type. Should be a boolean"), 400
        if 'level' in data:
            grade = data['level']
            if not isinstance(grade, int):
                return jsonify(error=f"Invalid 'level' type. Should be an integer"), 400
        if 'name' in data:
            user["name"] = data['name']
            user["time"] = datetime.datetime.now()
            user["score"] = 0
    if subject is None:
        return jsonify(error=f"Missing 'subject' parameter"), 400
    if random_options is None:
        return jsonify(error=f"Missing 'random_options' parameter"), 400
    if random_questions is None:
        return jsonify(error=f"Missing 'random_questions' parameter"), 400
    if on_spot_assessment is None:
        return jsonify(error=f"Missing 'spot_assess' parameter"), 400
    if grade is None:
        return jsonify(error=f"Missing 'level' parameter"), 400
    if grade == 2 and subject.lower() == "random":
        logger.logger.info(f"This combination is supported as of now")
        data= getQuestionsPage(grade, subject)
        return data
    else:
        logger.logger.error(f"This is not supported yet. Keep patience fore few more days")
        return jsonify(result=False)

def getQuestionsPage(grade, subject):
    if grade == 2 and subject == 'random':
        fp = 'Questionnaire/grade2/randomtest.csv'
        csv_data = []
        with open(fp, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                csv_data.append(row)
        json_output = json.dumps(csv_data, indent=4)
        logger.logger.info("I am now converting the csv to json", json.loads(json_output))
        filepath = 'Questionnaire/grade2/randomtest.json'
        if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, 'r') as file:
                data = json.load(file)
            print(data)
            return data
        else:
            return {}
    else:
        logger.logger.error(f"This is not supported yet")
        return jsonify(result=False)


@app.route('/', methods=["GET"])
def getexamdetails():
    response = render_template('sf.html')
    # Create a response object and add headers to it
    response_object = app.make_response(response)
    response_object.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response_object.headers['Pragma'] = 'no-cache'
    response_object.headers['Expires'] = '-1'
    return response_object

@app.route('/api/starttest', methods=["GET"])
def gettests():
    global questions
    args = request.args
    subject = args.get("subject")
    random_options = bool(args.get("random_options"))
    random_questions = bool(args.get("random_questions"))
    spot_assess = bool(args.get('spot_assess'))
    name = args.get("name")
    level = int(args.get('level'))
    logger.logger.info(f"Here I am {subject}, {random_questions}, {random_options}, {spot_assess}, {level}")
    headers = {"Content-Type": "application/json"}
    pload = {
        "name" : name,
        "subject": subject,
        "random_options": bool(random_options),
        "random_questions": bool(random_questions),
        "spot_assess": bool(spot_assess),
        "level": int(level)
    }
    logger.logger.info(f"Hitting this payload {json.dumps(pload)}")
    res = requests.post(url="http://localhost:5000/api/validateinput", data=json.dumps(pload), headers=headers)
    logger.logger.info(f"Here is the first question : {res.text}")
    questions = json.loads(res.text)['questions']
    if random_questions:
        random.shuffle(questions)
    if random_options:
        for q in questions:
            logger.logger.info(f"Here is the q data {q}")
            if 'question' in q:
                if 'options' in q['question']:
                    options_dict = q['question']['options']
                    shuffled_keys = list(options_dict.keys())
                    random.shuffle(shuffled_keys)
                    shuffled_options_dict = {key: options_dict[key] for key in shuffled_keys}
                    q['question']['options'] = shuffled_options_dict
    print(f"Jumbled data: {questions}")
    return render_template('index.html')

def getnextQuestion():
    global questions
    if len(questions) != 0:
        print("["+str(len(questions))+"]")
        return questions.pop()
    else:
        return {}

@app.route('/api/next_question', methods=["POST"])
def dummy():
    data = getnextQuestion()
    global user
    if data:
        question = data["question"]["name"]
        options = data["question"]["options"]
        expected = data["question"]["answer"]
        actual = request.form.get("selected_option")
        logger.logger.info(f"The total info of {user} is {expected}, {actual}")
        if len(answeredQuestions) == 1:
            if answeredQuestions.pop()["question"]["answer"][0] == actual:
                logger.logger.info("You answered correctly!!")
                user["score"] += 1
        answeredQuestions.append(data)
        if question and options and expected:
            return render_template('index.html', question=question, options=options, expected=expected)
        else:
            return jsonify(result="Incorrect question")
    else:
        actual = request.form.get("selected_option")
        if len(answeredQuestions) != 0:
            if answeredQuestions.pop()["question"]["answer"][0] == actual:
                logger.logger.info("You answered correctly!!")
                user["score"] += 1
            else:
                return jsonify(result=user, message="You already aubmitted the test!")
        return jsonify(result=user)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000)).start()
