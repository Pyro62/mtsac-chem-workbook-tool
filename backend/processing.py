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
    "2.12": "Word Problems",
    "2.13": "Percents",
    "2.14": "Averages",
    "2.15": "Direct and Inverse Proportions"
}

def get_student_name(student_row):

    # Get First/Last Name
    first_name = None if pd.isna(student_row["FirstName"]) else student_row["FirstName"]
    last_name = None if pd.isna(student_row["LastName"]) else student_row["LastName"]

    # Check if valid names, return with error if not
    if first_name == None or last_name == None:    # If either or both first or last is empty

        # Stores student record number for error output
        record_number = student_row.name+1
        
        # BOTH names are empty
        if first_name == None and last_name == None:
            print(f"ERROR -==- Both First Name and Last Name are EMPTY for record #{record_number}")
            
        # First name only is empty
        elif first_name == None:
            print(f"ERROR -==- First Name is EMPTY for record #{record_number}")
            
        # Last name only is empty
        elif last_name == None:
            print(f"ERROR -==- Last Name is EMPTY for record #{record_number}")
            
        # # UNCOMMENT AND CHANGE HERE IF SPECIFIC ERROR OUTPUT DESIRED | OTHERWISE OUTPUT IS (None, None)
        return (first_name, last_name)
    
    # Returns First and Last name as tuple (First, Last)
    full_name = (first_name, last_name)
    return full_name
    

# Function that iterates on a student row; looks specifically at missed points; save incorrect questions into list
# Parameter: A row from given from DF
# Returns: List of the questions student got wrong
def get_incorrect_questions(student_row):
    incorrect_question = []

    #CHANGE 30 LATER IN CASE MORE/LESS QUESTIONS (critical) -===- Completed
    # TYPO IN EXCEL SPREADSHEET  | "NumbeOfQuestions" has "Numbe" instead of "Number"
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

# Function Prints assessment results 
# Parameter: Dataframe with access to file
# Returns: VOID (But probably should return the something)
def process_assessment(df):

    #Get number of students (1 row = 1 student)
    num_students = df.shape[0]

    #student: [topics to review]
    result = dict()

    for student in range(num_students): 

        #Grabs the information for current student
        student_row = df.iloc[student]

        #Get student's name
        first_name, last_name = get_student_name(student_row)
        
        #Returns list of incorrect questions for current student
        incorrect_questions = get_incorrect_questions(student_row)

        #Returns list of topics student needs to review
        topics_to_review = get_topics_to_review(incorrect_questions, student_row)

        if first_name is None or last_name is None:
            result[f"Student #{student + 1}"] = topics_to_review
        else:
            result[f"{first_name} {last_name}"] = topics_to_review

    #FOR TESTING PURPOSES
    for student in result:
        print(student, result[student])

    print(type(result))
    return result


#----------------------USE FOR TESTING--------
# to test from this file, might need to use "cd mtsac-chem-workbook-tool\backend" to adjust path
#df = pd.read_excel('../test_data/assessment40.xlsx')
#df2 = pd.read_excel('../test_data/assessment10.xlsx')

#print("Assessment 1:")
#process_assessment(df)
#print("\nAssessment 2:")
#process_assessment(df2)


#Things to figure out later:

#2. wait for others to finish upload implementation

#   i) after waiting for ^^,  figure out how to pass df automatically

#5. Is "NumbeOfQuestions" going to be corrected? If so, correct them here


