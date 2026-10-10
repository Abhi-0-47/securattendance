# SecurAttendance: Multimodal Biometric Attendance Framework with Cryptographic Wage Auditing
### Public Works & Daily Wage Labor Protection Testbed (Indian Infrastructure Case Study)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg?style=flat&logo=python)](https://www.python.org)
[![Security](https://img.shields.io/badge/Cryptography-SHA--256%20%7C%20Merkle-10B981.svg?style=flat)](https://en.wikipedia.org/wiki/Merkle_tree)
[![Biometrics](https://img.shields.io/badge/PAD-ISO%2FIEC%2030107--3-06B6D4.svg?style=flat)](https://www.iso.org/standard/53227.html)
[![Currency](https://img.shields.io/badge/Currency-INR%20(₹)-F59E0B.svg?style=flat)](https://en.wikipedia.org/wiki/Indian_rupee)

A functional, academic-grade research prototype addressing real-world labor governance challenges in India: **ghost-worker fraud**, **contractor proxy-punching**, and **muster-roll wage theft** across construction sites, factories, and public infrastructure projects.

---

## 🏗️ Social Motivation & Engineering Architecture

In government public works and major infrastructure projects (e.g. metro rails, highways, housing), manual muster rolls and basic biometric systems are vulnerable to two major fraud vectors:
1. **Contractor Proxy Punching (Ghost Workers):** Middlemen hold up photo printouts or mobile screen recordings of absent workers to claim wages.
2. **Database Wage Tampering:** Site clerks or corrupt contractors alter attendance sheets after shifts to inflate work hours and pocket the difference.

This project delivers an end-to-end, mathematically verifiable solution:

```
+---------------------------------------------------------------------------------------------------------+
| TRACK 1: Edge Biometric & Anti-Proxy Liveness Check (AI/ML Module)                                      |
| Multi-Spectral PAD (Fourier Texture + Depth Disparity + Saccades) blocks contractor photo/screen spoofs  |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
| TRACK 2: Multi-Worksite Asynchronous Ingestion (Cloud Module)                                           |
| Field Site Terminal ➔ FastAPI Gateway (202 Accepted) ➔ Redis Muster Stream ➔ Celery Workers (<120ms)   |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼ (Only Verified Liveness Punches)
+---------------------------------------------------------------------------------------------------------+
| TRACK 3: Cryptographic Muster Roll & Wage Audit (Security Module)                                       |
| SHA-256 Hash Chained Shifts [H_i = H(H_{i-1} || Data_i)] ➔ Merkle Epoch Rollup ➔ Automated Wage Freeze  |
+---------------------------------------------------------------------------------------------------------+
```

---

## 👥 Localized Worker Registry (Sample Data)

| Worker ID | Name | Trade / Skill Category | Worksite Location | Daily Wage Rate |
| :--- | :--- | :--- | :--- | :--- |
| **WRK-MH-1042** | Rajesh Kumar | Senior Mason (Rajmistri) | Site #MH-04: Metro Depot, Mumbai | ₹750 / day |
| **WRK-MH-2089** | Ramesh Patil | Steel Rebar Fabricator | Site #MH-04: Metro Depot, Mumbai | ₹700 / day |
| **WRK-MH-3310** | Sunita Devi | Excavator & Heavy Machinery | Site #MH-04: Metro Depot, Mumbai | ₹800 / day |
| **WRK-MH-4105** | Mohammed Farooq | Master Site Electrician | Site #MH-04: Metro Depot, Mumbai | ₹850 / day |
| **WRK-MH-5520** | Lakshmi Bai | Material Logistics & Helper | Site #MH-04: Metro Depot, Mumbai | ₹600 / day |

---

## 🚀 How to Launch the Prototype

### 1. Start the Server
Run the automated launcher in your project directory:
```powershell
python run.py
```
*(Or double-click `run.bat` on Windows)*

The server will automatically open:
* **Interactive Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **OpenAPI / Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 4-Step Presentation Walkthrough for Examiners

1. **Step 1: Explain the Real-World Labor Problem (Track 1)**
   - Walk the committee through how ghost-worker fraud bleeds infrastructure budgets.
   - Punch in **Rajesh Kumar** legitimately to show genuine shift recording.
   - Switch to **"2D Printed Passport Photo"** or **"Mobile Video Replay"** to demonstrate how the multi-spectral PAD engine rejects the spoof attempt and drops the transaction with **₹0.00** credited.

2. **Step 2: Demonstrate Morning Rush Scalability (Track 2)**
   - Show how the FastAPI gateway buffers high-volume morning shift punches into Redis FIFO streams (`stream:muster_roll`).
   - Highlight the sub-100ms turnaround time and inspect real-time JSON payload traces passing to Celery worker nodes.

3. **Step 3: Demonstrate Tamper-Evident Wage Auditing (Track 3)**
   - Click **"Run Cryptographic Audit"** to confirm the initial 100% sealed muster roll.
   - Open the **Adversarial Tampering Tool**, select **Muster #2 (Ramesh Patil)**, and simulate a corrupt contractor inflating shifts from **1.0** to **2.5**.
   - Show the immediate detection: Shift #2 turns red, downstream blocks are flagged as invalidated by the avalanche effect, and the system **blocks corrupt wage disbursement** to protect public funds.

4. **Step 4: Review Theoretical & Defense Guide (Track 4)**
   - Walk through the mathematical formulas ($C_{pad}$, $H_i$, $N_{parent}$) and project architecture notes.
