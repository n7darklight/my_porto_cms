import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import base64

# Load environment variables from a .env file
load_dotenv()

# --- App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-very-secret-key-for-development')

# Trust headers from Cloudflare Tunnel
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# --- PostgreSQL Connection ---
DATABASE_URL = os.getenv('DATABASE_URL')

ENCODED_PW = os.getenv('ENCODED_CMS_PASSWORD')
if not ENCODED_PW:
    raise ValueError("ENCODED_CMS_PASSWORD must be set.")

# Decode from Base64 back to the original hash string
HASHED_CMS_PASSWORD = base64.b64decode(ENCODED_PW).decode('utf-8')

if not DATABASE_URL or not HASHED_CMS_PASSWORD:
    raise ValueError("DATABASE_URL and HASHED_CMS_PASSWORD must be set in the environment variables.")

# Database connection helper function
def get_db_connection():
    """Create and return a PostgreSQL database connection"""
    try:
        connection = psycopg2.connect(DATABASE_URL)
        return connection
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise

# ==============================================================================
# CMS ROUTES (For managing projects, requires login)
# ==============================================================================

# --- Login Page ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CMS Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="w-full max-w-xs">
        <form action="{{ url_for('login') }}" method="post" class="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
            <h1 class="text-2xl font-bold text-center mb-6">CMS Login</h1>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, message in messages %}
                  <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                    <span>{{ message }}</span>
                  </div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2" for="password">Password</label>
                <input class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" id="password" name="password" type="password" placeholder="******************">
            </div>
            <div class="flex items-center justify-between">
                <button class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline" type="submit">
                    Sign In
                </button>
            </div>
        </form>
    </div>
</body>
</html>
"""

@app.route('/cms/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if check_password_hash(HASHED_CMS_PASSWORD, password):
            session['logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('cms_dashboard'))
        else:
            flash('Incorrect password.', 'error')
            return redirect(url_for('login'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/cms/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- CMS Dashboard ---
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CMS Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8">
    <div class="container mx-auto">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-3xl font-bold">Project Dashboard</h1>
            <div>
                <a href="{{ url_for('add_project') }}" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Add New Project</a>
                <a href="{{ url_for('logout') }}" class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded ml-2">Logout</a>
            </div>
        </div>
        <div class="bg-white shadow-md rounded my-6 overflow-x-auto">
            <table class="min-w-full leading-normal">
                <thead>
                    <tr>
                        <th class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Title</th>
                        <th class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Showcased</th>
                        <th class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Order</th>
                        <th class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for project in projects %}
                    <tr>
                        <td class="px-5 py-5 border-b border-gray-200 bg-white text-sm"><p class="text-gray-900 whitespace-no-wrap">{{ project.title }}</p></td>
                        <td class="px-5 py-5 border-b border-gray-200 bg-white text-sm"><span class="relative inline-block px-3 py-1 font-semibold leading-tight {{ 'text-green-900' if project.is_showcased else 'text-gray-700' }}"><span aria-hidden class="absolute inset-0 {{ 'bg-green-200' if project.is_showcased else 'bg-gray-200' }} opacity-50 rounded-full"></span><span class="relative">{{ 'Yes' if project.is_showcased else 'No' }}</span></span></td>
                        <td class="px-5 py-5 border-b border-gray-200 bg-white text-sm"><p class="text-gray-900 whitespace-no-wrap">{{ project.display_order }}</p></td>
                        <td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
                            <a href="{{ url_for('edit_project', project_id=project.id) }}" class="text-indigo-600 hover:text-indigo-900">Edit</a>
                            <form action="{{ url_for('delete_project', project_id=project.id) }}" method="post" class="inline-block ml-4" onsubmit="return confirm('Are you sure you want to delete this project?');">
                                <button type="submit" class="text-red-600 hover:text-red-900">Delete</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/cms')
def cms_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Updated to explicitly use the porto_cms schema
        cursor.execute("SELECT * FROM porto_cms.porto_project_data ORDER BY display_order ASC")
        projects = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Convert RealDictRow to regular dict for template compatibility
        projects = [dict(project) for project in projects]
        return render_template_string(DASHBOARD_TEMPLATE, projects=projects)
    except Exception as e:
        print(f"Error fetching projects: {e}")
        flash('Error loading projects.', 'error')
        return redirect(url_for('login'))

# --- Add/Edit Project Page ---
PROJECT_FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ 'Edit' if project else 'Add' }} Project</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8">
    <div class="container mx-auto max-w-2xl">
        <h1 class="text-3xl font-bold mb-6">{{ 'Edit' if project else 'Add' }} Project</h1>
        <form action="{{ url_for('edit_project', project_id=project.id) if project else url_for('add_project') }}" method="post" class="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Title</label>
                <input type="text" name="title" value="{{ project.title or '' }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700" required>
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Short Description</label>
                <input type="text" name="short_description" value="{{ project.short_description or '' }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Long Description (Markdown supported)</label>
                <textarea name="long_description" rows="10" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">{{ project.long_description or '' }}</textarea>
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Image URL (e.g., /assets/images/projects/my_image.jpg)</label>
                <input type="text" name="image_url" value="{{ project.image_url or '' }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Technologies (comma-separated)</label>
                <input type="text" name="technologies" value="{{ project.technologies|join(', ') if project and project.technologies else '' }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">GitHub Link</label>
                <input type="url" name="github_link" value="{{ project.github_link or '' }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">
            </div>
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">Live Demo Link</label>
                <input type="url" name="live_demo_link" value="{{ project.live_demo_link or '' }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="block text-gray-700 text-sm font-bold mb-2">Display Order</label>
                    <input type="number" name="display_order" value="{{ project.display_order or 99 }}" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700">
                </div>
                <div class="flex items-center pt-6">
                    <input type="checkbox" name="is_showcased" id="is_showcased" class="mr-2" {{ 'checked' if project and project.is_showcased }}>
                    <label for="is_showcased" class="text-gray-700 text-sm font-bold">Showcase on Homepage?</label>
                </div>
            </div>
            <div class="flex items-center justify-start mt-6">
                <button type="submit" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Save Project</button>
                <a href="{{ url_for('cms_dashboard') }}" class="ml-4 text-gray-600">Cancel</a>
            </div>
        </form>
    </div>
</body>
</html>
"""

@app.route('/cms/add', methods=['GET', 'POST'])
def add_project():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            techs = [tech.strip() for tech in request.form.get('technologies', '').split(',') if tech.strip()]
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Updated to explicitly use the porto_cms schema
            cursor.execute("""
                INSERT INTO porto_cms.porto_project_data 
                (title, short_description, long_description, image_url, technologies, github_link, live_demo_link, is_showcased, display_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                request.form.get('title'),
                request.form.get('short_description'),
                request.form.get('long_description'),
                request.form.get('image_url'),
                techs,
                request.form.get('github_link'),
                request.form.get('live_demo_link'),
                'is_showcased' in request.form,
                int(request.form.get('display_order', 99))
            ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            flash('Project added successfully!', 'success')
            return redirect(url_for('cms_dashboard'))
        except Exception as e:
            print(f"Error adding project: {e}")
            flash('Error adding project.', 'error')
            return redirect(url_for('add_project'))

    return render_template_string(PROJECT_FORM_TEMPLATE, project=None)

@app.route('/cms/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        if request.method == 'POST':
            techs = [tech.strip() for tech in request.form.get('technologies', '').split(',') if tech.strip()]
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Updated to explicitly use the porto_cms schema
            cursor.execute("""
                UPDATE porto_cms.porto_project_data
                SET title = %s, short_description = %s, long_description = %s, 
                    image_url = %s, technologies = %s, github_link = %s, 
                    live_demo_link = %s, is_showcased = %s, display_order = %s
                WHERE id = %s
            """, (
                request.form.get('title'),
                request.form.get('short_description'),
                request.form.get('long_description'),
                request.form.get('image_url'),
                techs,
                request.form.get('github_link'),
                request.form.get('live_demo_link'),
                'is_showcased' in request.form,
                int(request.form.get('display_order', 99)),
                project_id
            ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            flash('Project updated successfully!', 'success')
            return redirect(url_for('cms_dashboard'))

        # GET request - fetch the project
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Updated to explicitly use the porto_cms schema
        cursor.execute("SELECT * FROM porto_cms.porto_project_data WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not project:
            flash('Project not found.', 'error')
            return redirect(url_for('cms_dashboard'))
        
        project = dict(project)
        return render_template_string(PROJECT_FORM_TEMPLATE, project=project)
    except Exception as e:
        print(f"Error: {e}")
        flash('Error processing request.', 'error')
        return redirect(url_for('cms_dashboard'))

@app.route('/cms/delete/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Updated to explicitly use the porto_cms schema
        cursor.execute("DELETE FROM porto_cms.porto_project_data WHERE id = %s", (project_id,))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        flash('Project deleted successfully!', 'success')
        return redirect(url_for('cms_dashboard'))
    except Exception as e:
        print(f"Error deleting project: {e}")
        flash('Error deleting project.', 'error')
        return redirect(url_for('cms_dashboard'))


# --- Main Entry Point ---
if __name__ == '__main__':
    # Listen on Nixpacks PORT or default to 5000. Debug disabled for prod.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)