import pandas as pd


# Function that gets student First and Last name and checks if valid
# Parameter: A row from given from DF
# Returns: If no name: tuple with None (None, None) | If valid: tuple (first_name, last_name)

#dict that maps topic num to chapters
TOPIC_MAP = {
    "2.1": "Positive and Negative Numbers",
    "2.2": "Number Line and Place Values",
    "2.3": "Number Sense",
    "2.4": "Math Notation",
    "2.5": "Fractions",
    "2.6": "Exponents",
    "2.7": "Orders of Operation",
    "2.8": "Scientific Notation",
    "2.9": "How to Use a Scientific Calculator",
    "2.10": "Solving Simple Algebraic Equations",
    "2.11": "Math with Units",
    "2.12": "Solving Word Problems",
    "2.13": "Percentages",
    "2.14": "Averages",
    "2.15": "Direct and Inverse Proportions",
    "2.16": "Graphing",
    "2.17": "Log and Inverse Log Functions"
}

def get_student_name(student_row):

    # Get First/Last Name
    first_name = None if pd.isna(student_row["FirstName"]) else student_row["FirstName"]
    last_name = None if pd.isna(student_row["LastName"]) else student_row["LastName"]
    
    # Returns First and Last name as tuple (First, Last)
    full_name = (first_name, last_name)
    return full_name
    

# Function that iterates on a student row; looks specifically at missed points; save incorrect questions into list
# Parameter: A row from given from DF
# Returns: List of the questions student got wrong
def get_incorrect_questions(student_row):
    incorrect_question = []

    num_of_questions = int(student_row["NumbeOfQuestions"])
    num_correct = student_row["NumberCorrect"]
    
    for questionNum in range(num_of_questions):

        points = student_row[f"EarnedPt{questionNum+1}"]

        if points == 0:
            incorrect_question.append(questionNum+1)

        # If found all incorrect answers (trusting columns "NumberCorerct" and "NumbeOfQuestions")
        if num_of_questions - num_correct < len(incorrect_question):
            break

    return incorrect_question


# Function finds topics student needs to review
# Parameter: List of questions student got wrong, A row given from DF
# Returns: List of topics student needs to review
def get_topics_to_review(student_incorrect_questions, student_row):
    topics_to_review = set()
    questions_per_topic = 2 

    for question in student_incorrect_questions:
        topic_count = int(student_row["NumbeOfQuestions"] / questions_per_topic)
        topic_num = question % topic_count
        if topic_num == 0:
            topic_num = topic_count

        # Create the key to look up ex, "2.1"
        topic_key = f"2.{topic_num}"
        
        # fetch from dict, if not there, return unknown topic
        topic_name = TOPIC_MAP.get(topic_key, "Unknown Topic")
        
        # Combine them: "2.1: Positive and Negative Numbers"
        full_topic_string = f"{topic_key}: {topic_name}"
        
        topics_to_review.add(full_topic_string)

    # Sorting logic remains similar, but now we must parse the float from the start of the string
    # We split by ":" to get "2.1" and convert to float for correct numerical sorting
    # Sorts by splitting "2.10: Topic" into (2, 10)
    topics_to_review = sorted(
        list(topics_to_review), 
        key=lambda x: [int(part) for part in x.split(":")[0].split(".")]
    )

    return topics_to_review


# Function get student id
# Parameter: student row and student number (index)
# Returns: student id string
def get_stu_id(student_row, student):
    stu_id = f"Temp ID #{student + 1}" if pd.isna(student_row["ZipGradeID"]) else student_row["ZipGradeID"]

    return stu_id


# Function get student test score
# Parameter: student row
# Returns: student test score string
def get_stu_score(student_row):
    stu_score = 0 if pd.isna(student_row["PercentCorrect"]) else student_row["PercentCorrect"]
    stu_score = f"{stu_score}%"
    return stu_score


# Function gets data for class (Average Scores, Most Missed Topics)
# Parameter: Dict containing all student's results
# Returns: Dict with {"missed_topics":list of topics in desc order, "average":float average scores}
def get_class_data(result_dict):
    count = len(result_dict)
    total = 0.0

    #Creates dict that tracks topic appearance count {"2.1":0, "2.2":0,...}
    topic_count_dict = dict.fromkeys(TOPIC_MAP.keys(), 0)

    # 
    for student_information in result_dict.values():
        #Adds flaot to total for average score
        #Uses string slicing to get rid of % sign
        total += float(student_information["score"][:-1])

        #Check and Increment all topics for this student
        for topic in student_information["topics_to_review"]:
            topic_count_dict[topic.split(":")[0]] += 1

    #Sorted list of tuples by decscending order [("2.7", 9), ("2.3", 8), ("2.2", 7)...]
    missed_topics = sorted(topic_count_dict.items(), key=lambda item: item[1], reverse=True)
    average = round(float(total/count), 2)

    class_data = {"missed_topics":missed_topics, "average":average}

    #Returns Dict of {"missed_topics":all topics in descending order, "average":average scores as float}
    return class_data


# Function Prints assessment results 
# Parameter: Dataframe with access to file
# Returns: VOID (But probably should return the something)
def process_assessment(df):

    #Get number of students (1 row = 1 student)
    num_students = df.shape[0]

    #Nested dictionary: id --> dictionary (name, score, topics to review)
    result = dict()

    for student in range(num_students):

        student_information = dict()

        #Grabs the information for current student
        student_row = df.iloc[student]

        #Get student's information
        first_name, last_name = get_student_name(student_row)
        stu_id = get_stu_id(student_row, student)
        stu_score = get_stu_score(student_row)

        #Get topics to review for student based on incorrect questions
        list_of_incorrect_questions = get_incorrect_questions(student_row)
        topics_to_review = get_topics_to_review(list_of_incorrect_questions, student_row)

        #Storing all information of student (name, score, topics to review)
        student_information["name"] = f"{first_name} {last_name}" if first_name and last_name else "Name Missing"
        student_information["score"] = stu_score
        student_information["topics_to_review"] = topics_to_review

        #Adding student id (key) and information (value) in dictionary

        #Student information keys: "name", "score", "topics_to_review"
        result[stu_id] = student_information


    return result

