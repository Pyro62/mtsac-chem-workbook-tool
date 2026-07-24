import io
import zipfile


def file_generator(results):
    zip_buffer = io.BytesIO()
    
    # open a ZipFile object in 'write' mode, using the buffer as the target
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        # iterate through results dict from processing
        for student, topics in results.items():
            # Create content for the text file
            file_content = f"Review Topics for {student}:\n" + "\n".join(topics)
            
            #add the file to the zip archive in memory, change for student name in future update
            filename = f"{student.replace(' ', '_')}_review.txt"
            zip_file.writestr(filename, file_content)
            
    #important reset the buffer pointer to the start so it can be read
    zip_buffer.seek(0)
    
    return zip_buffer