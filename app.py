"""
app.py — 數字易經分析 Web UI（Phase 2）

啟動：
  cd C:\\NumerologyEasing
  python app.py
  → http://127.0.0.1:5001
  （5000 給 SSS 即時監控用，避免衝突）

API：
  GET  /                      首頁
  POST /api/analyze           單串分析（手動模式）
  POST /api/auto              自動分析（id + phone + license）
  POST /api/age-mapping       身分證年齡分區
  POST /api/recommend         智能建議
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

import engine

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def api_analyze():
    data = request.get_json(silent=True) or {}
    seq = (data.get("input") or "").strip()
    mode = data.get("mode", "general")
    if not seq:
        return jsonify({"error": "input required"}), 400
    try:
        result = engine.analyze(seq, mode=mode)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@app.post("/api/auto")
def api_auto():
    data = request.get_json(silent=True) or {}
    out = {}
    if data.get("id"):
        try:
            out["id"] = engine.analyze(data["id"], mode="id")
            out["age_mapping"] = engine.age_mapping(data["id"])
        except (KeyError, ValueError) as e:
            out["id_error"] = str(e)
    if data.get("phone"):
        try:
            out["phone"] = engine.analyze(data["phone"], mode="general")
        except (KeyError, ValueError) as e:
            out["phone_error"] = str(e)
    if data.get("license"):
        try:
            out["license"] = engine.analyze(data["license"], mode="general")
        except (KeyError, ValueError) as e:
            out["license_error"] = str(e)
    return jsonify(out)


@app.post("/api/age-mapping")
def api_age_mapping():
    data = request.get_json(silent=True) or {}
    id_str = (data.get("id") or "").strip()
    if not id_str:
        return jsonify({"error": "id required"}), 400
    try:
        result = engine.age_mapping(id_str)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@app.post("/api/recommend")
def api_recommend():
    data = request.get_json(silent=True) or {}
    constraints = {
        "purpose": data.get("purpose", "phone"),
        "length": int(data.get("length", 10)),
        "prefix": data.get("prefix", ""),
        "exclude_magnets": data.get("exclude_magnets", []),
        "require_magnets": data.get("require_magnets", []),
        "candidate_pool": 2000,
    }
    top_n = int(data.get("top_n", 10))
    try:
        recs = engine.recommend(constraints, top_n=top_n)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"recommendations": recs, "constraints": constraints})


if __name__ == "__main__":
    # 本機：debug + 127.0.0.1
    # Render：用 gunicorn 跑（見 Procfile），不會進到這個分支
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host=host, port=port)
