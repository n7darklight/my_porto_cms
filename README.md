# Portfolio CMS

A simple, self-hosted Content Management System (CMS) for managing and showcasing portfolio projects.  
Built with Flask and MongoDB, it provides both public API endpoints and a password-protected admin dashboard.

## Features

- **Public API:** Fetch all projects, showcased projects, or a single project by ID.
- **Admin Dashboard:** Add, edit, delete, and reorder projects via a web interface.
- **Authentication:** Secure login for CMS access using a hashed password.
- **Modern UI:** Dashboard styled with Tailwind CSS.

## Setup

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

2. **Configure `.env`:**  
   Set your MongoDB URI, hashed password, and Flask secret key in `.env`.  
   See the provided `.env` example.

3. **Run the app:**
   ```sh
   python app.py
   ```

## Access

- **Public API:**  
  - `GET /api/projects/all` — All projects  
  - `GET /api/projects/showcased` — Top 3 showcased projects  
  - `GET /api/projects/<project_id>` — Project by ID

- **CMS Dashboard:**  
  - `http://localhost:5000/cms` (login required)

## License
MIT