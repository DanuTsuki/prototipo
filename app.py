import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, request, render_template_string, jsonify
import threading

app = Flask(__name__)

MAX_USERS = 100
SIMULATED_LATENCY_BASE = 0.1
SIMULATED_LATENCY_FACTOR = 0.001

results = []
TARGET_URL = ""

@app.route("/", methods=["GET", "POST"])
def home():
    global TARGET_URL
    if request.method == "POST":
        TARGET_URL = request.form.get("url")
        t = threading.Thread(target=lambda: asyncio.run(run_simulation()))
        t.start()
        return render_template_string("""
            <h2>La simulación ficticia para '{{url}}' se está ejecutando en segundo plano.</h2>
            <p>Progreso simulado: <span id="counter">0</span> usuarios procesados...</p>
            <p>Espera unos segundos y luego <a href='/graph'>haz clic aquí para ver los resultados</a>.</p>
            <script>
                const counter = document.getElementById("counter");
                async function fetchProgress() {
                    const res = await fetch("/progress");
                    const data = await res.json();
                    counter.innerText = data.processed;
                    if (data.processed < data.total) {
                        setTimeout(fetchProgress, 1000);
                    }
                }
                fetchProgress();
            </script>
        """, url=TARGET_URL)

    return render_template_string("""
        <h1>Simulador Ficticio de Tiempos de Respuesta</h1>
        <p>Ingresa la URL de referencia para la simulación (no se harán peticiones reales):</p>
        <form method="post">
            <input type="text" name="url" placeholder="https://ejemplo.com" size="50" required>
            <button type="submit">Iniciar Simulación</button>
        </form>
    """)

@app.route("/progress")
def progress():
    last_users = results[-1][0] if results else 0
    return jsonify(processed=last_users, total=MAX_USERS)

@app.route("/graph")
def graph():
    if not results:
        return "<h2>No hay resultados disponibles aún. Por favor, espera a que termine la simulación.</h2>"

    # ✅ Ordenar por número de usuarios para evitar líneas erráticas
    sorted_results = sorted(results, key=lambda x: x[0])
    users, times = zip(*sorted_results)
    derivative = np.gradient(times, users)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(users, times, marker='o', color='blue', label='T(u): Tiempo de respuesta simulado (s)')
    ax.set_xlabel('Usuarios concurrentes')
    ax.set_ylabel('Tiempo de respuesta simulado (s)')
    ax.set_xlim(min(users) - 5, max(users) + 5)
    ax.set_ylim(0, max(times)*1.2)
    ax.grid(True)

    # Etiquetas de cada punto
    for x, y in zip(users, times):
        ax.text(x, y, f"{y:.1f}s", fontsize=8, ha='center', va='bottom')

    ax2 = ax.twinx()
    ax2.plot(users, derivative, 'r--', marker='x', label="T'(u): Incremento por usuario (s)")
    ax2.set_ylabel("T'(u): Incremento por usuario (s)")
    ax2.set_ylim(min(derivative)*1.2, max(derivative)*1.2)

    for x, y in zip(users, derivative):
        ax2.text(x, y, f"{y:.3f}", fontsize=7, color='red', ha='center', va='bottom')

    # Línea del punto crítico
    punto_critico = next((u for u, d in zip(users, derivative) if d > 0.05), None)
    if punto_critico:
        ax.axvline(x=punto_critico, color='green', linestyle=':', label=f'Punto crítico: {punto_critico} usuarios')

    fig.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig("static/graph.png")

    punto_critico_texto = punto_critico if punto_critico else "No detectado"

    return render_template_string("""
        <h2>Resultados de la Simulación Ficticia para '{{url}}'</h2>
        <img src='/static/graph.png' width='800'>
        <h3>Interpretación de los resultados:</h3>
        <p>Este es un modelo simulado que estima cómo podría crecer el tiempo de respuesta si un servidor recibiera cada vez más usuarios concurrentes.</p>
        <p>La curva azul con puntos (T(u)) muestra los tiempos simulados para cada número de usuarios.</p>
        <p>La línea roja con cruces (T'(u)) indica la tasa de incremento del tiempo por usuario.</p>
        <p>La línea verde vertical representa el <strong>punto crítico estimado:</strong> {{critico}} usuarios, a partir del cual el rendimiento simulado empieza a degradarse fuertemente.</p>
        <p>Este análisis ficticio ilustra cómo se puede aplicar el modelado matemático con derivadas para anticipar problemas de rendimiento y planificar el escalamiento.</p>
        <p><a href='/'>Volver al inicio</a></p>
    """, url=TARGET_URL, critico=punto_critico_texto)

async def run_simulation():
    global results
    results = []
    for users in range(10, MAX_USERS + 1, 10):
        avg_response = await simulate_users(users)
        results.append((users, avg_response))

async def simulate_users(n_users):
    start = time.time()
    await asyncio.sleep(SIMULATED_LATENCY_BASE + SIMULATED_LATENCY_FACTOR * n_users * n_users)
    end = time.time()
    return end - start

if __name__ == "__main__":
    app.run(debug=True)
