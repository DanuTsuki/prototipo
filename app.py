import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, request, render_template_string, jsonify, send_file
import threading
import os

app = Flask(__name__)

# --- Configuración global ---
MAX_USERS = 100
USER_STEP = 10
SIMULATED_LATENCY_BASE = 0.1
SIMULATED_LATENCY_FACTOR = 0.001
DERIVATIVE_THRESHOLD = 0.05

results = []
TARGET_URL = ""
SIMULATION_RUNNING = False

# --- Página principal ---
@app.route("/", methods=["GET", "POST"])
def home():
    global TARGET_URL, SIMULATION_RUNNING

    if request.method == "POST":
        if SIMULATION_RUNNING:
            return render_template_string("""
                <h3>⏳ Una simulación ya está en curso. Por favor espera que finalice.</h3>
                <a href='/'>Volver</a>
            """)

        TARGET_URL = request.form.get("url").strip()
        if not TARGET_URL.startswith("http"):
            return "<h3>❌ URL inválida. Debe comenzar con http o https.</h3><a href='/'>Volver</a>"

        t = threading.Thread(target=lambda: asyncio.run(run_simulation()))
        t.start()

        return render_template_string("""
            <h2>🔍 Simulación iniciada para: '{{url}}'</h2>
            <p>Progreso: <span id="counter">0</span> usuarios procesados...</p>
            <script>
                const counter = document.getElementById("counter");
                async function checkProgress() {
                    const res = await fetch("/progress");
                    const data = await res.json();
                    counter.innerText = data.processed;
                    if (!data.finished) {
                        setTimeout(checkProgress, 1000);
                    }
                }
                checkProgress();
            </script>
            <p>Una vez finalizada, puedes revisar <a href='/results'>los resultados del análisis</a>.</p>
        """, url=TARGET_URL)

    return render_template_string("""
        <h1>🧠 Herramienta Inteligente de Simulación de Rendimiento Web</h1>
        <p>Ingresa la URL de tu sitio para estimar cómo se comportará ante carga creciente de usuarios.</p>
        <form method="post">
            <input type="text" name="url" placeholder="https://ejemplo.com" size="50" required>
            <button type="submit">Iniciar Simulación</button>
        </form>
        <p>✔️ Esta herramienta no hace peticiones reales. Todo es un modelo matemático.</p>
    """)

# --- Progreso actual ---
@app.route("/progress")
def progress():
    last_users = results[-1][0] if results else 0
    return jsonify(processed=last_users, total=MAX_USERS, finished=(last_users >= MAX_USERS))

# --- Resultados y análisis visual ---
@app.route("/results")
def results_view():
    if not results:
        return "<h2>⚠️ Aún no hay resultados disponibles.</h2><a href='/'>Volver</a>"

    sorted_results = sorted(results, key=lambda x: x[0])
    users, times = zip(*sorted_results)
    derivative = np.gradient(times, users)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(users, times, 'o-', color='blue', label='T(u): Tiempo de respuesta')
    ax.set_xlabel('Usuarios concurrentes')
    ax.set_ylabel('Tiempo (segundos)')
    ax.grid(True)

    ax2 = ax.twinx()
    ax2.plot(users, derivative, 'r--', marker='x', label="T'(u): Derivada")
    ax2.set_ylabel("T'(u): Crecimiento por usuario")

    critical_point = next((u for u, d in zip(users, derivative) if d > DERIVATIVE_THRESHOLD), None)
    if critical_point:
        ax.axvline(x=critical_point, color='green', linestyle=':', label=f'Punto crítico: {critical_point} usuarios')

    fig.legend(loc='upper left')
    fig.tight_layout()

    os.makedirs("static", exist_ok=True)
    fig.savefig("static/graph.png")

    tips = []
    if max(times) > 5:
        tips.append("🚨 El tiempo de respuesta supera los 5 segundos: considera escalar urgentemente.")
    if critical_point:
        tips.append(f"📈 Punto crítico estimado: {critical_point} usuarios.")
    else:
        tips.append("✅ No se detectaron problemas graves en esta simulación.")

    return render_template_string("""
        <h2>📊 Análisis del Tiempo de Respuesta para '{{url}}'</h2>
        <img src='/static/graph.png' width='800'><br>
        <h3>Resumen técnico:</h3>
        <ul>
            <li><strong>T(u)</strong>: Tiempo estimado en segundos para u usuarios concurrentes.</li>
            <li><strong>T'(u)</strong>: Cambio en tiempo por cada nuevo usuario (derivada).</li>
        </ul>
        <h3>🔔 Recomendaciones:</h3>
        <ul>
            {% for tip in tips %}<li>{{ tip }}</li>{% endfor %}
        </ul>
        <p><a href='/export'>Descargar CSV de resultados</a> | <a href='/'>Volver al inicio</a></p>
    """, url=TARGET_URL, tips=tips)

# --- Exportar resultados ---
@app.route("/export")
def export_data():
    if not results:
        return "<h3>No hay datos para exportar.</h3>"

    csv_path = "static/results.csv"
    with open(csv_path, "w") as f:
        f.write("usuarios,tiempo\n")
        for u, t in results:
            f.write(f"{u},{t:.4f}\n")

    return send_file(csv_path, as_attachment=True)

# --- Simulación asincrónica ---
async def run_simulation():
    global results, SIMULATION_RUNNING
    results = []
    SIMULATION_RUNNING = True

    for users in range(USER_STEP, MAX_USERS + 1, USER_STEP):
        t = await simulate_users(users)
        results.append((users, t))

    SIMULATION_RUNNING = False

# --- Simulación base ---
async def simulate_users(n_users):
    latency = SIMULATED_LATENCY_BASE + SIMULATED_LATENCY_FACTOR * (n_users ** 2)
    await asyncio.sleep(latency)
    return latency

# --- Iniciar app ---
if __name__ == "__main__":
    app.run(debug=True)