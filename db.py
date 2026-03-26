from pymongo import MongoClient

client = MongoClient("mongodb+srv://baglipika2005_db_user:admin123@clusterinternship01.1gmpvop.mongodb.net/")
db = client["psyconnect"]

students_col = db["students"]
mentors_col = db["mentors"]
psychologists_col = db["psychologists"]

def insert_students():
    students_col.delete_many({})
    students = []
    for i in range(1, 201):
        students.append({
            "studentId": f"SLRTCE/IT/TE{str(i).zfill(3)}",
            "name": f"Student {i}",
            "rollNo": i,
            "class": "TE. IT",
            "mentorId": f"MENTOR{str((i - 1) // 20 + 1).zfill(2)}",
            "psychologistId": "THERAPIST01" if i <= 100 else "THERAPIST02"
        })
    students_col.insert_many(students)
    print("✅ 200 Students Inserted!")

def insert_mentors():
    mentors_col.delete_many({})
    mentors = [
        {
            "mentorId": f"MENTOR{str(i).zfill(2)}",
            "name": f"Mentor {i}",
            "department": "IT",
            "assignedRollNos": f"{(i-1)*20 + 1} - {i*20}"
        }
        for i in range(1, 11)
    ]
    mentors_col.insert_many(mentors)
    print("✅ 10 Mentors Inserted!")

def insert_psychologists():
    psychologists_col.delete_many({})
    psychologists_col.insert_many([
        {
            "psychologistId": "THERAPIST01",
            "name": "Dr. A",
            "assignedRollNos": "1 - 100"
        },
        {
            "psychologistId": "THERAPIST02",
            "name": "Dr. B",
            "assignedRollNos": "101 - 200"
        }
    ])
    print("✅ 2 Psychologists Inserted!")

if __name__ == "__main__":
    insert_students()
    insert_mentors()
    insert_psychologists()
    print("\n🎉 All data inserted successfully!")