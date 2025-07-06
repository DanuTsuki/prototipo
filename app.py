import asyncio
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, request, render_template_string, jsonify
import threading
import io
import base64

app = Flask(__name__)

# Parámetros de simulación por defecto
MAX_USERS = 100
USER_STEP = 10
DERIVATIVE_THRESHOLD = 0.05

results = []
TARGET_URL = ""
SIMULATION_RUNNING = False

# Parámetros técnicos (a,b,k) calculados desde inputs amigables
param_a = 0.1
param_b = 0.001
param_k = 0.01

def estimar_a(tiempo_carga_min):
    return max(tiempo_carga_min, 0.01)

def estimar_b(tamano_pagina_mb, velocidad_mbps):
    factor_escala = 0.005
    if velocidad_mbps <= 0:
        velocidad_mbps = 1  # evitar división por cero
    b = (tamano_pagina_mb / velocidad_mbps) * factor_escala
    return max(b, 0.0001)

def estimar_k(num_usuarios_max):
    if num_usuarios_max <= 0:
        num_usuarios_max = 50
    base = 0.1
    k = base * (50 / num_usuarios_max)
    return max(min(k, 0.1), 0.001)

@app.route("/", methods=["GET", "POST"])
def home():
    global TARGET_URL, SIMULATION_RUNNING, param_a, param_b, param_k, MAX_USERS, USER_STEP

    if request.method == "POST":
        if SIMULATION_RUNNING:
            return render_template_string(PROGRESS_TEMPLATE, url=TARGET_URL, mensaje="⏳ Simulación en curso. Espera a que finalice.")

        TARGET_URL = request.form.get("url").strip()
        if not TARGET_URL.startswith("http"):
            return render_template_string(HOME_TEMPLATE, error="❌ URL inválida. Debe comenzar con http o https.")

        try:
            tiempo_base = float(request.form.get("tiempo_base"))
            tamano_pagina = float(request.form.get("tamano_pagina"))
            velocidad_internet = float(request.form.get("velocidad_internet"))
            max_usuarios = int(request.form.get("max_usuarios"))
            paso_usuarios = int(request.form.get("paso_usuarios"))
        except Exception:
            return render_template_string(HOME_TEMPLATE, error="❌ Por favor ingresa valores válidos para todos los campos numéricos.")

        if tiempo_base < 0 or tamano_pagina <= 0 or velocidad_internet <= 0 or max_usuarios <= 0 or paso_usuarios <= 0:
            return render_template_string(HOME_TEMPLATE, error="❌ Todos los valores deben ser mayores que cero.")

        param_a = estimar_a(tiempo_base)
        param_b = estimar_b(tamano_pagina, velocidad_internet)
        param_k = estimar_k(max_usuarios)
        MAX_USERS = max_usuarios
        USER_STEP = paso_usuarios

        threading.Thread(target=lambda: asyncio.run(run_simulation())).start()

        return render_template_string(PROGRESS_TEMPLATE, url=TARGET_URL, mensaje=None)

    return render_template_string(HOME_TEMPLATE)

@app.route("/progress")
def progress():
    last_users = results[-1][0] if results else 0
    return jsonify(processed=last_users, total=MAX_USERS, finished=(last_users >= MAX_USERS))

@app.route("/results")
def results_view():
    if not results:
        return render_template_string(HOME_TEMPLATE, error="⚠️ No hay resultados. Ejecuta una simulación primero.")

    sorted_results = sorted(results, key=lambda x: x[0])
    users, times = zip(*sorted_results)
    derivative = np.gradient(times, users)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(users, times, 'o-', label='T(u): Tiempo de respuesta (s)')
    ax.set_xlabel('Usuarios concurrentes')
    ax.set_ylabel('Tiempo de respuesta (s)')
    ax.grid(True)

    ax2 = ax.twinx()
    ax2.plot(users, derivative, 'r--', marker='x', label="T'(u): Derivada")
    ax2.set_ylabel("Derivada")

    critical_point = next((u for u, d, t in zip(users, derivative, times) if d > DERIVATIVE_THRESHOLD or t > 1.0), None)
    if critical_point:
        ax.axvline(x=critical_point, color='green', linestyle=':', label=f'Punto crítico: {critical_point} usuarios')

    fig.legend(loc='upper left')
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    graph_base64 = base64.b64encode(buf.read()).decode('utf-8')

    tips = []
    max_time = max(times)

    if max_time > 5:
        tips.append("🚨 Latencia máxima > 5s: se recomienda escalar o mejorar infraestructura.")
    elif max_time > 2:
        tips.append("⚠️ Latencia máxima > 2s: monitorear rendimiento para evitar degradación.")
    elif max_time > 1:
        tips.append("⚠️ Latencia máxima > 1s: puede afectar la experiencia de usuario.")
    else:
        tips.append("👍 Latencia aceptable para la mayoría de usuarios.")

    if critical_point:
        tips.append(f"📈 Punto crítico detectado alrededor de {critical_point} usuarios concurrentes.")
        tips.append(f"🔍 Se recomienda no superar este límite para evitar lentitud.")

    return render_template_string(RESULTS_TEMPLATE, url=TARGET_URL, graph=graph_base64, tips=tips)

async def run_simulation():
    global results, SIMULATION_RUNNING, USER_STEP, MAX_USERS
    results = []
    SIMULATION_RUNNING = True

    current = USER_STEP
    while current < MAX_USERS:
        t = calcular_tiempo_respuesta(current)
        results.append((current, t))
        await asyncio.sleep(0.1)
        current += USER_STEP

    if not results or results[-1][0] != MAX_USERS:
        t = calcular_tiempo_respuesta(MAX_USERS)
        results.append((MAX_USERS, t))

    SIMULATION_RUNNING = False

def calcular_tiempo_respuesta(u):
    # Modelo: T(u) = a + b * exp(k * u)
    return param_a + param_b * np.exp(param_k * u)

# === Plantillas HTML con CSS embebido ===

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Simulación de Rendimiento Web</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f5f7fa;
      margin: 0;
      padding: 20px;
      color: #333;
    }
    h1 {
      color: #004d99;
      text-align: center;
      margin-bottom: 30px;
    }
    form {
      background-color: #fff;
      max-width: 600px;
      margin: auto;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 0 15px rgba(0,0,0,0.1);
    }
    input[type="text"],
    input[type="number"] {
      width: 100%;
      padding: 10px 8px;
      margin: 8px 0 20px 0;
      border: 1px solid #ccc;
      border-radius: 5px;
      font-size: 1rem;
      box-sizing: border-box;
      transition: border-color 0.3s;
    }
    input[type="text"]:focus,
    input[type="number"]:focus {
      border-color: #004d99;
      outline: none;
    }
    label {
      font-weight: 600;
      display: block;
      margin-bottom: 5px;
      color: #004d99;
    }
    button {
      background-color: #004d99;
      color: white;
      padding: 12px 20px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 1.1rem;
      width: 100%;
      transition: background-color 0.3s ease;
    }
    button:hover {
      background-color: #003366;
    }
    p, a {
      text-align: center;
      color: #555;
    }
    a {
      text-decoration: none;
      color: #004d99;
      font-weight: 600;
    }
    a:hover {
      text-decoration: underline;
    }
    .error {
      background-color: #f8d7da;
      border: 1px solid #f5c6cb;
      color: #721c24;
      padding: 10px;
      margin-bottom: 20px;
      border-radius: 5px;
      max-width: 600px;
      margin-left: auto;
      margin-right: auto;
      text-align: center;
    }
  </style>
</head>
<body>
  <h1>🧠 Herramienta de Simulación de Rendimiento Web</h1>
  
  {% if error %}
    <div class="error">{{error}}</div>
  {% endif %}
  
  <form method="post" novalidate>
      <input type="text" name="url" placeholder="https://ejemplo.com" size="50" required><br>

      <label>Tiempo base de carga sin usuarios (segundos):</label>
      <input type="number" name="tiempo_base" step="0.01" min="0" value="0.2" required>

      <label>Tamaño promedio de la página (MB):</label>
      <input type="number" name="tamano_pagina" step="0.01" min="0.01" value="1.5" required>

      <label>Velocidad promedio de internet (Mbps):</label>
      <input type="number" name="velocidad_internet" step="0.1" min="0.1" value="10" required>

      <label>Número máximo de usuarios concurrentes a simular:</label>
      <input type="number" name="max_usuarios" min="1" max="1000" value="100" required>

      <label>Incremento de usuarios por paso en simulación:</label>
      <input type="number" name="paso_usuarios" min="1" max="100" value="10" required>

      <button type="submit">Iniciar simulación</button>
  </form>
</body>
</html>
"""

PROGRESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Simulación en curso</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f5f7fa;
      margin: 0;
      padding: 20px;
      color: #333;
      text-align: center;
    }
    h2 {
      color: #004d99;
      margin-bottom: 10px;
    }
    p {
      font-size: 1.1rem;
      margin-bottom: 15px;
    }
    #counter {
      font-weight: 700;
      color: #007bff;
    }
    a {
      color: #004d99;
      text-decoration: none;
      font-weight: 600;
    }
    a:hover {
      text-decoration: underline;
    }
    .mensaje {
      max-width: 600px;
      margin: 20px auto;
      background-color: #f8d7da;
      border: 1px solid #f5c6cb;
      color: #721c24;
      padding: 15px;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <h2>🔍 Simulación iniciada para: '{{url}}'</h2>
  
  {% if mensaje %}
    <div class="mensaje">{{mensaje}}</div>
  {% else %}
    <p>Progreso: <span id="counter">0</span> usuarios procesados...</p>
    <p>Este proceso puede tardar unos minutos. Cuando acabe será dirigido a los resultados.</p>
  {% endif %}

  <script>
    const counter = document.getElementById("counter");
    let lastCount = 0;

    async function checkProgress() {
        const res = await fetch("/progress");
        const data = await res.json();

        if(data.processed > lastCount) {
            lastCount++;
            counter.innerText = lastCount;
            setTimeout(checkProgress, 50);
        } else {
            if (!data.finished) {
                setTimeout(checkProgress, 1000);
            } else {
                window.location.href = '/results';
            }
        }
    }

    if (!{{ 'true' if mensaje else 'false' }}) {
        checkProgress();
    }
  </script>
</body>
</html>
"""

RESULTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Resultados de Simulación</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f5f7fa;
      margin: 0;
      padding: 20px;
      color: #333;
    }
    h2 {
      color: #004d99;
      text-align: center;
      margin-bottom: 25px;
    }
    img {
      display: block;
      margin: 0 auto 30px auto;
      max-width: 90%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 0 15px rgba(0,0,0,0.1);
    }
    ul {
      max-width: 700px;
      margin: auto;
      padding-left: 20px;
      color: #555;
      font-size: 1.1rem;
      list-style-type: disc;
    }
    li {
      margin-bottom: 10px;
    }
    a {
      display: block;
      width: 150px;
      margin: 30px auto 0 auto;
      text-align: center;
      background-color: #004d99;
      color: white;
      padding: 12px 0;
      text-decoration: none;
      font-weight: 600;
      border-radius: 6px;
      transition: background-color 0.3s ease;
    }
    a:hover {
      background-color: #003366;
    }
  </style>
</head>
<body>
  <h2>📊 Resultados de simulación para '{{url}}'</h2>
  <img src="data:image/png;base64,{{graph}}" alt="Gráfico de resultados">
  
  <h3>Recomendaciones y alertas:</h3>
  <ul>
    {% for tip in tips %}
      <li>{{ tip }}</li>
    {% endfor %}
  </ul>
  
  <a href="/">Volver</a>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
