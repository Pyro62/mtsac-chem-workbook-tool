import pandas as pd

# Function that iterates on a student row; looks specifically at missed points; save incorrect questions into list
# Parameter: A row from given from DF
# Returns: List of the questions student got wrong
def get_incorrect_questions(student_row):
    incorrect_question = []

    #CHANGE 30 LATER IN CASE MORE/LESS QUESTIONS
    for questionNum in range(30):

        points = student_row[f"EarnedPt{questionNum+1}"]

        if points == 0:
            incorrect_question.append(questionNum+1)

    return incorrect_question


# Function finds topics student needs to review
# Parameter: List of questions student got wrong
# Returns: List of topics student needs to review
def get_topics_to_review(student_incorrect_questions):
    topics_to_review = set()

    for question in student_incorrect_questions:

        topic = question % 15
        if topic == 0:
            topic = 15

        #Add "2.num" to specifiy the chapter students should review (e.g. 2.15, 2.4)
        topic = f"2.{topic}"
            
        topics_to_review.add(topic)

    topics_to_review = sorted(topics_to_review)

    return topics_to_review


# Function Prints assessment results 
# Parameter: Dataframe with access to file
# Returns: VOID (But probably should return the something)
def process_assessment(df):

    num_students = df.shape[0]  #Get number of students (1 row = 1 student)
    

    for student in range(num_students): 

        #Grabs the information for current student
        student_row = df.iloc[student]
        
        #Returns list of incorrect questions for current student
        incorrect_questions = get_incorrect_questions(student_row)

        #Returns list of topics student needs to review
        topics_to_review = get_topics_to_review(incorrect_questions)


        print(f"Student {student + 1} needs to review topics: {topics_to_review}")


#----------------------USE FOR TESTING--------
df = pd.read_excel('../test_data/assessment40.xlsx')
df2 = pd.read_excel('../test_data/assessment10.xlsx')

print("Assessment 1:")
process_assessment(df)
print("\nAssessment 2:")
process_assessment(df2)

#Things to figure out later:
'''1. how to automate df access
2. how to find num of questions in test
3. implement automated reporting instead of running program manually'''

