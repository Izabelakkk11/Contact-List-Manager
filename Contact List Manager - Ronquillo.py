from flask import Flask, request, jsonify, redirect, url_for
import json
import os
import requests

app = Flask(__name__)

CONTACTS_FILE = 'contacts.json'
HUBSPOT_CLIENT_ID = '0a65ab4b-b349-4823-9d5e-cfd7136aa1df'
HUBSPOT_CLIENT_SECRET = 'e04f0501-4d93-4be7-a601-1556e287fcfc'
HUBSPOT_REDIRECT_URI = 'http://localhost:5000/callback'
HUBSPOT_AUTH_URL = 'https://app.hubspot.com/oauth/authorize'
HUBSPOT_TOKEN_URL = 'https://api.hubapi.com/oauth/v1/token'
HUBSPOT_API_BASE_URL = 'https://api.hubapi.com/contacts/v1/contact'

# Load contacts from JSON file
def load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return {"contacts": [], "emergency_contact": None}
    
    with open(CONTACTS_FILE, 'r') as f:
        return json.load(f)

# Save contacts to JSON file
def save_contacts(data):
    with open(CONTACTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Function to get access token
def get_access_token(code):
    data = {
        'grant_type': 'authorization_code',
        'client_id': HUBSPOT_CLIENT_ID,
        'client_secret': HUBSPOT_CLIENT_SECRET,
        'redirect_uri': HUBSPOT_REDIRECT_URI,
        'code': code
    }
    response = requests.post(HUBSPOT_TOKEN_URL, data=data)
    return response.json()

# Function to add a contact to HubSpot
def add_contact_to_hubspot(access_token, contact):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(HUBSPOT_API_BASE_URL, headers=headers, json=contact)
    if response.status_code != 200:
        print(f"Failed to add contact to HubSpot: {response.text}")
        return False
    return True

# Function to update a contact in HubSpot
def update_contact_in_hubspot(access_token, contact_id, contact):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.put(f"{HUBSPOT_API_BASE_URL}/vid/{contact_id}", headers=headers, json=contact)
    if response.status_code != 200:
        print(f"Failed to update contact in HubSpot: {response.text}")
        return False
    return True

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contact List Manager</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #B6B2A5;
                margin: 0;
                padding: 0;
            }
          .container {
                width: 80%;
                max-width: 600px;
                margin: 0 auto; /* Center the container */
                padding: 20px;
                background-color: #FFF2D7;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }
            h1 {
                display: flex;
                align-items: center;
                justify-content: center;
                color: #000000;
            }
            h2.emergency {
                color: red;
            }
            form {
                display: flex;
                flex-direction: column;
            }
            label {
                margin-bottom: 10px;
                font-size: 1.2em;
                color: #8B5A2B;
            }
            input[type="text"], input[type="email"], input[type="checkbox"] {
                padding: 10px;
                font-size: 1em;
                border: 4px solid #ccc;
                border-radius: 4px;
                margin-bottom: 20px;
                color: #000000;
            }
            button {
                padding: 10px 20px;
                font-size: 1em;
                color: #fff;
                background-color: #B07B3C;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background-color: #A67C52;
            }
            ul {
                list-style-type: none;
                padding: 0;
            }
            li {
                margin: 10px 0;
                font-size: 1.1em;
                color: #000000;
                border: 1px solid #ccc;
                padding: 10px;
                border-radius: 4px;
                position: relative;
            }
            .delete-btn {
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                cursor: pointer;
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: #ff0000;
                color: #ffffff;
            }
            .edit-btn {
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                cursor: pointer;
                position: absolute;
                top: 10px;
                right: 80px;
                background-color: #007BFF;
                color: #ffffff;
            }
            .logo {
                margin-right: 10px;
                margin-left: 10px;
                height: auto;
                width: 23%; 
            }
        </style>
    </head>
    <body>
     <div class="container">  
            <h1 style="display: flex; align-items: left; justify-content: left">
                <img src="/static/logo.png" alt="Logo" class="logo">
                <span style="margin-left: 10px;">Contact List Manager</span>
        </h1>
        <hr>
            <form id="contactForm">
                <input type="hidden" id="edit_index" value="-1">
                <label for="contact_name">Enter contact name:</label>
                <input type="text" id="contact_name" placeholder="Contact Name" required>

                <label for="contact_phone">Enter phone number:</label>
                <input type="text" id="contact_phone" placeholder="Phone Number" maxlength="11" required oninput="limitPhoneNumber(this)">

                <label for="contact_email">Enter email address:</label>
                <input type="email" id="contact_email" placeholder="Email Address" required>

                <label for="contact_relationship">Enter relationship:</label>
                <input type="text" id="contact_relationship" placeholder="e.g., Family, Friend" required>

                <label>
                    <input type="checkbox" id="emergency_contact"> Mark as emergency contact
                </label>

                <button type="button" id="addBtn" onclick="addContact()">Add Contact</button>
                <button type="button" id="saveBtn" style="display:none;" onclick="saveContact()">Save Contact</button>
            </form>
            
            <label for="searchBar">Search Contacts:</label>
            <input type="text" id="searchBar" placeholder="Search by name..." oninput="searchContacts()"><hr>

            <h2>Contact List:</h2>
            <ul id="contactList"></ul>

            <hr><h2 class="emergency">Emergency Contact:</h2>
            <ul id="emergencyContactList"></ul>
        </div>

        <script>
            let contacts = [];
            let emergencyContact = null;

            async function fetchContacts() {
                const response = await fetch('/get_contacts');
                const data = await response.json();
                contacts = data.contacts;
                emergencyContact = data.emergency_contact;
                displayContacts();
                displayEmergencyContact();
            }

            function displayContacts() {
                const contactList = document.getElementById('contactList');
                contactList.innerHTML = '';

                contacts.sort((a, b) => a.name.localeCompare(b.name));

                contacts.forEach((contact, index) => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <div><strong>Name:</strong> ${contact.name}</div>
                        <div><strong>Relationship:</strong> ${contact.relationship}</div>
                        <div><strong>Phone:</strong> ${contact.phone}</div>
                        <div><strong>Email:</strong> ${contact.email}</div>
                        <button class="edit-btn" onclick="editContact(${index})">Edit</button>
                        <button class="delete-btn" onclick="deleteContact(${index})">Delete</button>
                    `;
                    contactList.appendChild(li);
                });
            }

            function displayEmergencyContact() {
                const emergencyContactList = document.getElementById('emergencyContactList');
                emergencyContactList.innerHTML = '';

                if (emergencyContact) {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <div><strong>Name:</strong> ${emergencyContact.name}</div>
                        <div><strong>Relationship:</strong> ${emergencyContact.relationship}</div>
                        <div><strong>Phone:</strong> ${emergencyContact.phone}</div>
                        <div><strong>Email:</strong> ${emergencyContact.email}</div>
                        <button class="delete-btn" onclick="deleteEmergencyContact()">Delete</button>
                    `;
                    emergencyContactList.appendChild(li);
                }
            }

            async function addContact() {
                    const name = document.getElementById('contact_name').value;
                    const phone = document.getElementById('contact_phone').value;
                    const email = document.getElementById('contact_email').value;
                    const relationship = document.getElementById('contact_relationship').value;
                    const isEmergency = document.getElementById('emergency_contact').checked;

                    // Validation to check if all fields are filled
                if (!name || !phone || !email || !relationship) {
                    alert("Please fill in all required fields.");
                return;
            }

    const contactData = { name, phone, email, relationship, isEmergency };

    // Check for existing contact
    const existingContactIndex = contacts.findIndex(contact => contact.name.toLowerCase() === name.toLowerCase());
    if (existingContactIndex !== -1) {
        alert("Contact already exists.");
        return;
    }

    const response = await fetch('/add_contact', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(contactData)
    });

    if (response.ok) {
        document.getElementById('contactForm').reset();
        fetchContacts();
    } else {
        const errorData = await response.json();
        alert(errorData.error);
    }
}

            async function editContact(index) {
                document.getElementById('edit_index').value = index;
                document.getElementById('contact_name').value = contacts[index].name;
                document.getElementById('contact_phone').value = contacts[index].phone;
                document.getElementById('contact_email').value = contacts[index].email;
                document.getElementById('contact_relationship').value = contacts[index].relationship;
                document.getElementById('emergency_contact').checked = contacts[index].isEmergency;

                document.getElementById('saveBtn').style.display = 'inline-block';
                document.getElementById('addBtn').style.display = 'none';
            }

            async function saveContact() {
                const index = document.getElementById('edit_index').value;
                const name = document.getElementById('contact_name').value;
                const phone = document.getElementById('contact_phone').value;
                const email = document.getElementById('contact_email').value;
                const relationship = document.getElementById('contact_relationship').value;
                const isEmergency = document.getElementById('emergency_contact').checked;

                const contactData = { name, phone, email, relationship, isEmergency };

                const response = await fetch(`/update_contact/${index}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(contactData)
                });

                if (response.ok) {
                    // Set or remove emergency contact
                    if (isEmergency) {
                        const emergencyResponse = await fetch(`/set_emergency_contact/${index}`, {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(contactData)
                        });
                        if (!emergencyResponse.ok) {
                            alert("Failed to set as emergency contact");
                        }
                    } else {
                        // If unchecked, remove emergency contact
                        const emergencyResponse = await fetch(`/delete_emergency_contact`, {
                            method: 'DELETE'
                        });
                        if (!emergencyResponse.ok) {
                            alert("Failed to remove emergency contact");
                        }
                    }

                    document.getElementById('contactForm').reset();
                    document.getElementById('saveBtn').style.display = 'none';
                    document.getElementById('addBtn').style.display = 'inline-block';
                    fetchContacts();
                    
                } else {
                    const errorData = await response.json();
                    alert(errorData.error);
                }
            }

            async function deleteContact(index) {
                    const confirmDelete = confirm("Are you sure you want to delete this contact?");

                if (!confirmDelete) {
                    return; // Exit the function if the user cancels
                }

                    const response = await fetch(`/delete_contact/${index}`, { method: 'DELETE' });
                    if (response.ok) {
                    fetchContacts();

                } else {
                const errorData = await response.json();
                    alert(errorData.error);
                }
            }

            async function deleteEmergencyContact() {
                    const confirmDelete = confirm("Are you sure you want to delete the emergency contact?");
                if (!confirmDelete) {
                    return; // Exit the function if the user cancels
                }

                    const response = await fetch('/delete_emergency_contact', { method: 'DELETE' });

                if (response.ok) {
                    fetchContacts();

                } else {
                    const errorData = await response.json();
                    alert(errorData.error);
                }
            }

            function limitPhoneNumber(input) {
                const value = input.value.replace(/\D/g, '').substring(0, 11);
                input.value = value;
            }

            function searchContacts() {
                const searchTerm = document.getElementById('searchBar').value.toLowerCase();
                const filteredContacts = contacts.filter(contact => contact.name.toLowerCase().includes(searchTerm));
                const contactList = document.getElementById('contactList');
                contactList.innerHTML = '';

                filteredContacts.forEach((contact, index) => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <div><strong>Name:</strong> ${contact.name}</div>
                        <div><strong>Relationship:</strong> ${contact.relationship}</div>
                        <div><strong>Phone:</strong> ${contact.phone}</div>
                        <div><strong>Email:</strong> ${contact.email}</div>
                        <button class="edit-btn" onclick="editContact(${index})">Edit</button>
                        <button class="delete-btn" onclick="deleteContact(${index})">Delete</button>
                    `;
                    contactList.appendChild(li);
                });
            }

            window.onload = fetchContacts;
        </script>
    </body>
    </html>
    '''

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    data = load_contacts()
    return jsonify(data)

@app.route('/add_contact', methods=['POST'])
def add_contact():
    contact = request.json
    data = load_contacts()
    data['contacts'].append(contact)
    
    if contact.get('isEmergency'):
        data['emergency_contact'] = contact

    save_contacts(data)
    return jsonify(success=True)

@app.route('/update_contact/<int:index>', methods=['PUT'])
def update_contact(index):
    contact = request.json
    data = load_contacts()

    if 0 <= index < len(data['contacts']):
        data['contacts'][index] = contact
        save_contacts(data)
        return jsonify(success=True)
    return jsonify(success=False), 404

@app.route('/set_emergency_contact/<int:index>', methods=['PUT'])
def set_emergency_contact(index):
    contact = request.json
    data = load_contacts()

    if 0 <= index < len(data['contacts']):
        # Set the emergency contact
        data['emergency_contact'] = contact
        save_contacts(data)
        return jsonify(success=True)
    return jsonify(success=False), 404

@app.route('/delete_contact/<int:index>', methods=['DELETE'])
def delete_contact(index):
    data = load_contacts()

    if 0 <= index < len(data['contacts']):
        del data['contacts'][index]
        save_contacts(data)
        return jsonify(success=True)
    return jsonify(success=False), 404

@app.route('/delete_emergency_contact', methods=['DELETE'])
def delete_emergency_contact():
    data = load_contacts()
    data['emergency_contact'] = None 
    save_contacts(data)
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)