from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import logging
import json
import os

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# Function to load notes from JSON file and calculate tag statistics
def load_notes():
    with open('notes.json', 'r') as file:
        notes = json.load(file)
    
    # Set initial pinned status of each note
    for note in notes:
        note['pinned'] = note.get('pinned', False)
        
    # Set initial flashcard status of each note
    for note in notes:
        note['flashcard'] = note.get('flashcard', False)
        
    # Find number of pinned notes
    num_pinned = 0
    for note in notes:
        if note['pinned'] == True:
            num_pinned = num_pinned + 1
    
    # Set original position of each note
    pos = 0
    for note in notes:
        note['original_pos'] = note.get('original_pos', pos)
        pos = pos + 1
        
    # Calculate tag statistics
    tags = {}
    total_notes = len(notes)
    for note in notes:
        if 'tags' in note:
            tag = note['tags'] or 'Other'
            tags[tag] = tags.get(tag, 0) + 1
        else:
            tags['Other'] = tags.get('Other', 0) + 1

    # Calculate percentage of notes with each tag
    tag_percentages = {tag: int(count / total_notes * 100) for tag, count in tags.items()}

    return notes, tags, total_notes, tag_percentages, num_pinned

# Function to load notebooks from JSON file 
def load_notebooks():
    with open('notebooks.json', 'r') as file:
        notes = json.load(file)
    return notes

# Function to save notes to JSON file
def save_notes(notes):
    with open('notes.json', 'w') as file:
        json.dump(notes, file, indent=4)


# Custom filter to format datetime
@app.template_filter('format_datetime')
def format_datetime(value):
    if value:
        datetime_obj = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        return datetime_obj.strftime('%B %d, %Y %I:%M %p')
    return ''

# Add a new note
@app.route('/add', methods=['GET', 'POST'])
def add_note():
    if request.method == 'POST':
        notes, tags, total_notes, tag_percentages, _ = load_notes()  # Unpack the tuple
        note = {
            'title': request.form['title'],
            'content': request.form['content'],
            'tags': request.form['tags'],
            'color': request.form['color'] if 'color' in request.form else '#ffffff',
            'reminder': request.form['reminder'] if 'reminder' in request.form else '',
            'pinned': False,
            'original_pos': len(notes),
            'flashcard': request.form['flashcard'] if 'flashcard' in request.form else False
        }
        notes.append(note)
        save_notes(notes)
        return redirect(url_for('index'))
    return render_template('add.html')

# Delete notes
@app.route('/delete/<int:note_id>')
def delete_note(note_id):
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    reversed_notes = list(reversed(notes))
    del reversed_notes[note_id]
    notes = list(reversed(reversed_notes))  # Update the original notes list
    save_notes(notes)
    return redirect(url_for('index', editModeStatus="on"))

# Clear filter
@app.route('/clear_filter')
def clear_filter():
    return redirect(url_for('index'))

# Clear date filter
@app.route('/clear_date_filter')
def clear_date_filter():
    return redirect(url_for('index'))

# Filter notes
@app.route('/filter_notes', methods=['POST'])
def filter_notes():
    filter_content = request.form.get('filter', '').lower()
    notes, tags, total_notes, tag_percentages, _ = load_notes()
    filtered_notes = [note for note in notes if filter_content in note['content'].lower()]
    tags = {}
    total_notes = len(filtered_notes)
    for note in filtered_notes:
        if 'tags' in note:
            tag = note['tags'] or 'Other'
            tags[tag] = tags.get(tag, 0) + 1
        else:
            tags['Other'] = tags.get('Other', 0) + 1
    # Calculate percentage of notes with each tag
    tag_percentages = {tag: int(count / total_notes * 100) for tag, count in tags.items()}
    return render_template('index.html', notes=filtered_notes, filter_content=filter_content, tag_percentages=tag_percentages)

# Function to calculate tag statistics
def calculate_tag_percentages(notes):
    tags = {}
    total_notes = len(notes)

    for note in notes:
        if 'tags' in note:
            tag = note['tags'] or 'Other'
            tags[tag] = tags.get(tag, 0) + 1
        else:
            tags['Other'] = tags.get('Other', 0) + 1

    tag_percentages = {tag: int(count / total_notes * 100) for tag, count in tags.items()}

    return tag_percentages

# Filter notes by today's date or previous days
@app.route('/filter_notes_by_today', methods=['POST'])
def filter_notes_by_today():
    notes, tags, total_notes, tag_percentages, _ = load_notes()
    filtered_notes = []
    
    for note in notes:
        reminder = note.get('reminder')
        if reminder:
            try:
                reminder_date = datetime.strptime(reminder, '%Y-%m-%dT%H:%M')
                if reminder_date.date() <= datetime.now().date():
                    filtered_notes.append(note)
            except ValueError:
                pass
    tags = {}
    total_notes = len(filtered_notes)
    for note in filtered_notes:
        if 'tags' in note:
            tag = note['tags'] or 'Other'
            tags[tag] = tags.get(tag, 0) + 1
        else:
            tags['Other'] = tags.get('Other', 0) + 1

    # Calculate percentage of notes with each tag
    tag_percentages = {tag: int(count / total_notes * 100) for tag, count in tags.items()}
    
    return render_template('index.html', notes=filtered_notes, total_notes=total_notes, tag_percentages=tag_percentages)

@app.route('/')
def index():
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    reversed_notes = list(reversed(notes))
    total_notes = len(notes)
    tag_percentages = calculate_tag_percentages(notes)  # Calculate the tag percentages
    # Get the current edit mode status from the query parameters
    edit_mode_status = request.args.get('editModeStatus', 'off')
    return render_template('index.html', notes=reversed_notes, total_notes=total_notes, tag_percentages=tag_percentages, editModeStatus=edit_mode_status)

# Toggle edit mode
@app.route('/toggle_edit_mode', methods=['POST'])
def toggle_edit_mode():
    edit_mode = request.form.get('edit_mode')
    if edit_mode == "on":
        edit_mode = "off"
    else:
        edit_mode = "on"
    return redirect(url_for('index', editModeStatus=edit_mode))


@app.route('/edit', methods=['GET'])
def select_note_to_edit():
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    return render_template('edit.html', notes=notes)

# Edit a note
@app.route('/edit/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    reversed_notes = list(reversed(notes))
    note = reversed_notes[note_id]
    if request.method == 'POST':
        note['title'] = request.form.get('title', '')
        note['content'] = request.form.get('content', '')
        note['tags'] = request.form.get('tags', '')
        note['color'] = request.form.get('color', '#ffffff')
        note['reminder'] = request.form.get('reminder', '')
        note['flashcard'] = request.form.get('flashcard', False)
        save_notes(notes)
        return redirect(url_for('index'))
    return render_template('edit.html', note=note, note_id=note_id)

# Pin a note
@app.route('/pin/<int:note_id>', methods=['POST'])
def pin_note(note_id):
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    notes = list(reversed(notes))
    note = notes[note_id]
    note['pinned'] = True
    notes.remove(note)
    notes.insert(0, note)  # Insert the note at the beginning of the list (top)
    save_notes(list(reversed(notes)))
    return redirect(url_for('index'))

# Unpin a note
@app.route('/unpin/<int:note_id>', methods=['POST'])
def unpin_note(note_id):
    notes, _, _, _, num_pinned = load_notes()  # Only need the notes, so unpack the first element
    notes = list(reversed(notes))
    note = notes[note_id]
    original_position = note['original_pos']
    note['pinned'] = False
    notes.remove(note)
    notes = list(reversed(notes))
    notes_p1 = []
    for value in notes:
        if value['pinned'] == False:
            notes_p1.append(value)
        else:
            break
        if value['original_pos'] > original_position:
            notes_p1.pop()
            notes_p1.append(note)
            break
    if note not in notes_p1:
        notes_p1.append(note)
    new_index = notes_p1.index(note)
    notes_p2 = notes[new_index:]
    combined_notes = notes_p1 + notes_p2
    save_notes(combined_notes)
    return redirect(url_for('index'))

@app.route('/flash')
def flash_load():
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    true_notes = []
    for note in notes: 
        if note['flashcard'] == "on":
            true_notes.append(note)   
    flashcards = list(reversed(true_notes))
    total_notes = len(flashcards)
    tag_percentages = calculate_tag_percentages(flashcards)  # Calculate the tag percentages

    return render_template('flash.html', notes=flashcards, total_notes=total_notes, tag_percentages=tag_percentages)

@app.route('/view_flash')
def view_flash():
    return redirect(url_for('flash_load'))

# Clear flashcards filter
@app.route('/clear_flash_filter')
def clear_flash_filter():
    return redirect(url_for('flash_load'))

# Filter flashcards
@app.route('/filter_flash', methods=['POST'])
def filter_flash():
    filter_content = request.form.get('filterf', '').lower()
    notes, tags, total_notes, tag_percentages, _ = load_notes()
    for note in notes: 
        if note['flashcard'] == False:
            notes.remove(note)     
    filtered_notes = [note for note in notes if filter_content in note['content'].lower()]
    tags = {}
    total_notes = len(filtered_notes)
    for note in filtered_notes:
        if 'tags' in note:
            tag = note['tags'] or 'Other'
            tags[tag] = tags.get(tag, 0) + 1
        else:
            tags['Other'] = tags.get('Other', 0) + 1
    tag_percentages = {tag: int(count / total_notes * 100) for tag, count in tags.items()}
    return render_template('flash.html', notes=filtered_notes, filter_content=filter_content, tag_percentages=tag_percentages)

@app.route('/quiz')
def quiz_load():
    notes, _, _, _, _ = load_notes()  # Only need the notes, so unpack the first element
    flashcards = [note for note in notes if note['flashcard']]
    return render_template('quiz.html', flashcards=flashcards)

@app.route('/notes')
def notes_load():
    notes = load_notebooks()  # Only need the notes, so unpack the first element
    sel_note = notes[0]["title"]
    sel_chap = notes[0]["chapters"][0]["title"]
    chapters = notes[0]["chapters"]
    return render_template('notes.html', notebooks=notes, selected_notebook=sel_note, selected_chapter=sel_chap, chapters=chapters, selected_chapter_index=0)

@app.route('/notes_update', methods=['POST'])
def update_json():
    notes = load_notebooks()
    # Get the data and other variables from the request
    data = request.form.get('data')
    index = int(request.form.get('selected_chapter_index'))
    selected_notebook = request.form.get('selected_notebook')
    selected_chapter = request.form.get('selected_chapter')
    chapters = []
    for nb in notes:
        if nb["title"] == selected_notebook:
            chapters = nb["chapters"]
    if 0 <= index < len(notes):
        for nb in notes:
            if nb["title"] == selected_notebook:
                nb["chapters"][index]["content"] = data
                break
    # Write the data to the JSON file
    with open('notebooks.json', 'w') as file:
        json.dump(notes, file)
    return render_template('notes.html', notebooks=notes, selected_notebook=selected_notebook, selected_chapter=selected_chapter, selected_chapter_index=index, chapters=chapters)


@app.route('/show_notebook/<notebook>')
def show_notebook(notebook):
    notebooks = load_notebooks()
    selected_notebook = notebook
    index = 0
    for nb in notebooks:
        if nb["title"] == notebook:
            selected_chapter = nb["chapters"][0]["title"]
            chapters = nb["chapters"]
            break
    return render_template('notes.html', notebooks=notebooks, selected_notebook=selected_notebook, selected_chapter=selected_chapter, chapters=chapters, selected_chapter_index=index)


@app.route('/show_chapter/<notebook>/<chapter>')
def show_chapter(notebook, chapter):
    notebooks = load_notebooks()
    selected_notebook = notebook
    selected_chapter = chapter
    index = 0
    for nb in notebooks:
        if nb["title"] == notebook:
            chapters = nb["chapters"]
    for chap in chapters:
        if chap["title"] == selected_chapter:
            break
        index = index + 1
    return render_template('notes.html', notebooks=notebooks, selected_notebook=selected_notebook, selected_chapter=selected_chapter, chapters=chapters, selected_chapter_index=index)

@app.route('/add_section/<notebook>')
def add_section(notebook):
    notebooks = load_notebooks()
    sel_chap = ''
    chapters = []
    for nb in notebooks:
        if nb["title"] == notebook:
            str2 = 'Chapter ' + str(len(nb["chapters"]) + 1)
            new_chap = {'title': str2}
            nb["chapters"].append(new_chap)
            sel_chap = nb["chapters"][0]["title"]
            chapters = nb["chapters"]
            break
    with open('notebooks.json', 'w') as file:
        json.dump(notebooks, file)
    return render_template('notes.html', notebooks=notebooks, selected_notebook=notebook, selected_chapter=sel_chap, selected_chapter_index=0, chapters=chapters)

@app.route('/delete_section/<notebook>/<sel_index>')
def delete_section(notebook, sel_index):
    notebooks = load_notebooks()
    chapters = []
    for nb in notebooks:
        if nb["title"] == notebook:
            nb["chapters"].pop(int(sel_index))
            sel_chap = nb["chapters"][0]["title"]
            chapters = nb["chapters"]
            break
    with open('notebooks.json', 'w') as file:
        json.dump(notebooks, file)
    return render_template('notes.html', notebooks=notebooks, selected_notebook=notebook, selected_chapter=sel_chap, selected_chapter_index=0, chapters=chapters)

@app.route('/add_notebook')
def add_notebook():
    notes = load_notebooks()  # Only need the notes, so unpack the first element
    sel_note = notes[0]["title"]
    sel_chap = notes[0]["chapters"][0]["title"]
    chapters = notes[0]["chapters"]
    str2 = 'Notebook ' + str(len(notes) + 1)
    new_notebook = {'title' : str2, 'chapters' : ['Chapter 1']}
    notes.append(new_notebook)
    with open('notebooks.json', 'w') as file:
        json.dump(notes, file)
    return render_template('notes.html', notebooks=notes, selected_notebook=sel_note, selected_chapter=sel_chap, chapters=chapters, selected_chapter_index=0)


# Rest of the code...
if __name__ == '__main__':
    # Create an empty notes file if it doesn't exist
    if not os.path.exists('notes.json'):
        with open('notes.json', 'w') as file:
            json.dump([], file)

    app.run(debug=True)
