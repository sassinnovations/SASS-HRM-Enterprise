# SASS HRM: Connected Overview, Products and Projects

- Dashboard metrics and shortcuts open the real, role-appropriate modules: staff/profile, attendance, leave, recruitment or learning, organization, calendar, reporting, and HR support. The supporting browser test checks the route or action reached.
- Products has a dedicated catalog with code, name, description, category and status. It is separate from the equipment register; the dashboard keeps its equipment preview and Asset Management link.
- Projects has a separate register with an optional employee owner and start/end dates, distinct from Project Timesheets. The two screens link to each other; existing timesheet project names are left untouched and are not re-mapped.
- An HR administrator can add, edit, filter and delete records, and configure categories and a default status in each register. Delete asks for confirmation and archives the record, keeping its code reserved and its audit history intact.
- Both modules are available from Overview and under Employee Services. HR administrators also find the module links in the Administration settings center. Existing staff access to their equipment and timesheets is unchanged.
- The approved borderless White and Blue sign-in is included.

## Updating your existing installation

1. Back up your existing project and database. Stop the SASS HRM frontend and backend.
2. Merge this ZIP's project files into the existing **White and Blue** project folder (the one containing START_LOCAL_DEV.bat). Keep the existing root and server environment files, MySQL volume and any custom deployment configuration. The archive does not contain .env credentials or a database dump.
3. Restart using the existing startup method. Do not run initial setup again, remove volumes, or reset the database. The regular backend startup installs the two new tables without rewriting existing records. If the application's MySQL account lacks CREATE permission, have your DBA run only database/26_PRODUCT_PROJECT_CATALOG_ADD_ONLY.sql on the existing database, then retry startup.
4. Open Overview and select Products or Projects.

Testing used a disposable SQLite database; offline MySQL schema and SQL adapter checks are included. It was not deployed to or run against your live MySQL database.
