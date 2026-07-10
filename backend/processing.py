import pandas as pd


# Function that gets student First and Last name and checks if valid
# Parameter: A row from given from DF
# Returns: If no name: tuple with None (None, None) | If valid: tuple (first_name, last_name)
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
        # return (first_name, last_name)
    
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

    for question in student_incorrect_questions:

        #Change 15 LATER IN CASE MORE/LESS TOPICS (critical) -==- DONE
        # SET AT DEFAULT 2 | Change if assessment has different amount of questions per topic
        # questions_per_topic can also be hooked up to parameter in website if wanted
        questions_per_topic = 2 

        # Currently requires access to column "NumbeOfQuestions" for automatic topic count
        topic_count = int(student_row["NumbeOfQuestions"] / questions_per_topic)
        topic = question % topic_count
        if topic == 0:
            topic = topic_count

        #Add "2.num" to specifiy the chapter students should review (e.g. 2.15, 2.4)
        topic = f"2.{topic}"
            
        topics_to_review.add(topic)

    # Sorts Results (prioritizes length of string [single or double diget], then value of float)
    topics_to_review = sorted(topics_to_review, key=lambda x: (len(x), float(x)))

    # Returns sorted set of strings (e.g. {"2.1", "2.10", "2.15"})
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
        
        #Returns list of incorrect questions for current student
        incorrect_questions = get_incorrect_questions(student_row)

        #Returns list of topics student needs to review
        topics_to_review = get_topics_to_review(incorrect_questions, student_row)

        #For testing
        result[f"Student #{student + 1}"] = topics_to_review
    
    for student in result:
        print(student, result[student])
    return result


#----------------------USE FOR TESTING--------
#df = pd.read_excel('../test_data/assessment40.xlsx')
#df2 = pd.read_excel('../test_data/assessment10.xlsx')

print("Assessment 1:")
#process_assessment(df)
print("\nAssessment 2:")
#process_assessment(df2)


#Things to figure out later:
#1. add function to get student name; error handling if name is missing
# DONE! Only need to customize output if you want a specific output
# I did not hook it up to anywhere, I'm not sure where it should go
# Currently students are identified by student_row.name+1 and student+1, which are both the student's number 

#2. wait for others to finish upload implementation

#   i) after waiting for ^^,  figure out how to pass df automatically

#5. Is "NumbeOfQuestions" going to be corrected? If so, correct them here


# Tasks Completed:

#3. in get_incorrect_questions function, add error handling or automatic detection of number of questions so it isnt fixed
# at 30 iterations
# Automatic Detection DONE! Retrieves it based off of value in column "NumbeOfQuestions"

#4. in get_topics_to_review function, add error handling or automatic detection of number of topics so it isnt fixed
# at 15 iterations
# DONE! Changed: get_topics_to_review to have extra parameter of student_row to have access to column "NumbeOfQuestions"
# for auto detection 
# Also, can allow for user customization for questions_per_topic variable
