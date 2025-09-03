from __future__ import annotations

import os
from typing import List

from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
# Allow overriding DB via env var; default to a local SQLite file
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tracker.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

db = SQLAlchemy(app)


# --- Models ---
class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    projects = db.relationship("Project", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - repr convenience
        return f"<Client {self.name!r}>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)

    client = db.relationship("Client", back_populates="projects")
    modules = db.relationship("Module", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("client_id", "name", name="uq_project_client_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project {self.name!r} of client_id={self.client_id}>"


class Module(db.Model):
    __tablename__ = "modules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    project = db.relationship("Project", back_populates="modules")
    entries = db.relationship("ModuleEntry", back_populates="module", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("project_id", "name", name="uq_module_project_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Module {self.name!r} of project_id={self.project_id}>"


entry_developer = db.Table(
    "entry_developer",
    db.Column("entry_id", db.Integer, db.ForeignKey("module_entries.id"), primary_key=True),
    db.Column("developer_id", db.Integer, db.ForeignKey("developers.id"), primary_key=True),
)


class Developer(db.Model):
    __tablename__ = "developers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Developer {self.name!r}>"


class ModuleEntry(db.Model):
    __tablename__ = "module_entries"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id"), nullable=False)

    event_id = db.Column(db.String(64), nullable=True)
    template_type = db.Column(db.String(255), nullable=True)
    subevents_count = db.Column(db.Integer, nullable=True)

    estimated_efforts = db.Column(db.Float, nullable=True)
    actual_efforts = db.Column(db.Float, nullable=True)

    content_integration_status = db.Column(db.String(64), nullable=True)  # e.g. Done/Pending
    assets_alignment_status = db.Column(db.String(64), nullable=True)
    comments = db.Column(db.Text, nullable=True)

    module = db.relationship("Module", back_populates="entries")
    developers = db.relationship("Developer", secondary=entry_developer, lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Entry id={self.id} module_id={self.module_id}>"


# --- DB bootstrap ---
def ensure_db_created() -> None:
    # Create tables if they don't exist (SQLite file will be created automatically)
    with app.app_context():
        db.create_all()


@app.route("/")
def index():
    return redirect(url_for("list_clients"))


# ---- Clients ----
@app.route("/clients")
def list_clients():
    clients = Client.query.order_by(Client.name.asc()).all()
    return render_template("clients/list.html", clients=clients)


@app.route("/clients/new", methods=["GET", "POST"])
def create_client():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Client name is required", "danger")
        else:
            client = Client(name=name, description=description)
            db.session.add(client)
            db.session.commit()
            flash("Client created", "success")
            return redirect(url_for("list_clients"))
    return render_template("clients/form.html", client=None)


@app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
def edit_client(client_id: int):
    client = Client.query.get_or_404(client_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Client name is required", "danger")
        else:
            client.name = name
            client.description = description
            db.session.commit()
            flash("Client updated", "success")
            return redirect(url_for("list_clients"))
    return render_template("clients/form.html", client=client)


@app.route("/clients/<int:client_id>/delete", methods=["POST"])
def delete_client(client_id: int):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash("Client deleted", "success")
    return redirect(url_for("list_clients"))


# ---- Projects ----
@app.route("/clients/<int:client_id>/projects")
def list_projects(client_id: int):
    client = Client.query.get_or_404(client_id)
    projects = Project.query.filter_by(client_id=client_id).order_by(Project.name.asc()).all()
    return render_template("projects/list.html", client=client, projects=projects)


@app.route("/clients/<int:client_id>/projects/new", methods=["GET", "POST"])
def create_project(client_id: int):
    client = Client.query.get_or_404(client_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Project name is required", "danger")
        else:
            project = Project(name=name, description=description, client_id=client_id)
            db.session.add(project)
            db.session.commit()
            flash("Project created", "success")
            return redirect(url_for("list_projects", client_id=client_id))
    return render_template("projects/form.html", client=client, project=None)


@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Project name is required", "danger")
        else:
            project.name = name
            project.description = description
            db.session.commit()
            flash("Project updated", "success")
            return redirect(url_for("list_projects", client_id=project.client_id))
    client = Client.query.get(project.client_id)
    return render_template("projects/form.html", client=client, project=project)


@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    client_id = project.client_id
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted", "success")
    return redirect(url_for("list_projects", client_id=client_id))


# ---- Modules ----
@app.route("/projects/<int:project_id>/modules")
def list_modules(project_id: int):
    project = Project.query.get_or_404(project_id)
    modules = Module.query.filter_by(project_id=project_id).order_by(Module.name.asc()).all()
    # Totals per module shown on modules page via aggregation in template
    return render_template("modules/list.html", project=project, modules=modules)


@app.route("/projects/<int:project_id>/modules/new", methods=["GET", "POST"])
def create_module(project_id: int):
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Module name is required", "danger")
        else:
            module = Module(name=name, description=description, project_id=project_id)
            db.session.add(module)
            db.session.commit()
            flash("Module created", "success")
            return redirect(url_for("list_modules", project_id=project_id))
    return render_template("modules/form.html", project=project, module=None)


@app.route("/modules/<int:module_id>/edit", methods=["GET", "POST"])
def edit_module(module_id: int):
    module = Module.query.get_or_404(module_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Module name is required", "danger")
        else:
            module.name = name
            module.description = description
            db.session.commit()
            flash("Module updated", "success")
            return redirect(url_for("list_modules", project_id=module.project_id))
    project = Project.query.get(module.project_id)
    return render_template("modules/form.html", project=project, module=module)


@app.route("/modules/<int:module_id>/delete", methods=["POST"])
def delete_module(module_id: int):
    module = Module.query.get_or_404(module_id)
    project_id = module.project_id
    db.session.delete(module)
    db.session.commit()
    flash("Module deleted", "success")
    return redirect(url_for("list_modules", project_id=project_id))


# ---- Developers ----
@app.route("/developers")
def list_developers():
    developers = Developer.query.order_by(Developer.name.asc()).all()
    return render_template("developers/list.html", developers=developers)


@app.route("/developers/new", methods=["GET", "POST"])
def create_developer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Developer name is required", "danger")
        else:
            dev = Developer(name=name)
            db.session.add(dev)
            db.session.commit()
            flash("Developer created", "success")
            return redirect(url_for("list_developers"))
    return render_template("developers/form.html", developer=None)


@app.route("/developers/<int:developer_id>/edit", methods=["GET", "POST"])
def edit_developer(developer_id: int):
    developer = Developer.query.get_or_404(developer_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Developer name is required", "danger")
        else:
            developer.name = name
            db.session.commit()
            flash("Developer updated", "success")
            return redirect(url_for("list_developers"))
    return render_template("developers/form.html", developer=developer)


@app.route("/developers/<int:developer_id>/delete", methods=["POST"])
def delete_developer(developer_id: int):
    developer = Developer.query.get_or_404(developer_id)
    db.session.delete(developer)
    db.session.commit()
    flash("Developer deleted", "success")
    return redirect(url_for("list_developers"))


# ---- Entries ----
@app.route("/modules/<int:module_id>/entries")
def list_entries(module_id: int):
    module = Module.query.get_or_404(module_id)
    entries = ModuleEntry.query.filter_by(module_id=module_id).order_by(ModuleEntry.id.asc()).all()
    # Totals
    total_estimated = sum((e.estimated_efforts or 0) for e in entries)
    total_actual = sum((e.actual_efforts or 0) for e in entries)
    return render_template(
        "entries/list.html",
        module=module,
        entries=entries,
        total_estimated=total_estimated,
        total_actual=total_actual,
    )


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


@app.route("/modules/<int:module_id>/entries/new", methods=["GET", "POST"])
def create_entry(module_id: int):
    module = Module.query.get_or_404(module_id)
    all_devs = Developer.query.order_by(Developer.name.asc()).all()
    if request.method == "POST":
        entry = ModuleEntry(
            module_id=module_id,
            event_id=request.form.get("event_id") or None,
            template_type=request.form.get("template_type") or None,
            subevents_count=_parse_int(request.form.get("subevents_count")),
            estimated_efforts=_parse_float(request.form.get("estimated_efforts")),
            actual_efforts=_parse_float(request.form.get("actual_efforts")),
            content_integration_status=request.form.get("content_integration_status") or None,
            assets_alignment_status=request.form.get("assets_alignment_status") or None,
            comments=request.form.get("comments") or None,
        )
        dev_ids = request.form.getlist("developer_ids")
        if dev_ids:
            entry.developers = Developer.query.filter(Developer.id.in_(dev_ids)).all()
        db.session.add(entry)
        db.session.commit()
        flash("Entry created", "success")
        return redirect(url_for("list_entries", module_id=module_id))
    return render_template("entries/form.html", module=module, entry=None, developers=all_devs)


@app.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
def edit_entry(entry_id: int):
    entry = ModuleEntry.query.get_or_404(entry_id)
    module = Module.query.get(entry.module_id)
    all_devs = Developer.query.order_by(Developer.name.asc()).all()
    if request.method == "POST":
        entry.event_id = request.form.get("event_id") or None
        entry.template_type = request.form.get("template_type") or None
        entry.subevents_count = _parse_int(request.form.get("subevents_count"))
        entry.estimated_efforts = _parse_float(request.form.get("estimated_efforts"))
        entry.actual_efforts = _parse_float(request.form.get("actual_efforts"))
        entry.content_integration_status = request.form.get("content_integration_status") or None
        entry.assets_alignment_status = request.form.get("assets_alignment_status") or None
        entry.comments = request.form.get("comments") or None

        dev_ids = request.form.getlist("developer_ids")
        entry.developers = Developer.query.filter(Developer.id.in_(dev_ids)).all() if dev_ids else []

        db.session.commit()
        flash("Entry updated", "success")
        return redirect(url_for("list_entries", module_id=entry.module_id))
    return render_template("entries/form.html", module=module, entry=entry, developers=all_devs)


@app.route("/entries/<int:entry_id>/delete", methods=["POST"])
def delete_entry(entry_id: int):
    entry = ModuleEntry.query.get_or_404(entry_id)
    module_id = entry.module_id
    db.session.delete(entry)
    db.session.commit()
    flash("Entry deleted", "success")
    return redirect(url_for("list_entries", module_id=module_id))


# --- App startup ---
ensure_db_created()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

