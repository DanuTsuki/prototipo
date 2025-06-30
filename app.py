import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# Configuración básica de simulación
TARGET_URL = "https://example.com"  # Cambia a tu servidor real
MAX_USERS = 300
SIMULATED_LATENCY_BASE = 0.1  # 100 ms base
SIMULATED_LATENCY_FACTOR = 0.001  # Crecimiento por usuario

results = []  # (usuarios, tiempo de respuesta promedio)

@app.route("/")
def home():
    return render_template_string("""
        <h1>Simulador de Tiempos de Respuesta</h1>
        <p>Haz clic para ejecutar la simulación:</p>
        <a href='/simulate'>Iniciar Simulación</a>
    """)

@app.route("/simulate")
def simulate():
    global results
    results = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_simulation())
    return render_template_string("""
        <h2>Simulación completada</h2>
        <p><a href='/graph'>Ver gráficos</a></p>
    """)

@app.route("/graph")
def graph():
    users, times = zip(*results)
    # Calcular derivada aproximada (diferencias finitas)
    derivative = np.gradient(times, users)

    fig, ax = plt.subplots()
    ax.plot(users, times, label='T(u): Tiempo de respuesta (s)')
    ax.set_xlabel('Usuarios concurrentes')
    ax.set_ylabel('Tiempo de respuesta (s)')
    ax.grid(True)

    ax2 = ax.twinx()
    ax2.plot(users, derivative, 'r--', label="T'(u): Derivada")
    ax2.set_ylabel("T'(u): Incremento por usuario (s)")

    fig.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig("static/graph.png")

    return render_template_string("""
        <h2>Resultados de la Simulación</h2>
        <img src='/static/graph.png' width='800'>
        <p><a href='/'>Volver al inicio</a></p>
    """)

async def run_simulation():
    global results
    for users in range(10, MAX_USERS + 1, 10):
        avg_response = await simulate_users(users)
        results.append((users, avg_response))

async def simulate_users(n_users):
    start = time.time()
    # Simula latencia base + carga creciente
    await asyncio.sleep(SIMULATED_LATENCY_BASE + SIMULATED_LATENCY_FACTOR * n_users * n_users)
    end = time.time()
    return end - start

if __name__ == "__main__":
    app.run(debug=True)
