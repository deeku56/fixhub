document.addEventListener("DOMContentLoaded", function () {
  // ================= LOGIN / REGISTER =================
  async function register() {
    const email = document.getElementById("auth-email")?.value.trim();
    const password = document.getElementById("auth-password")?.value.trim();
    const status = document.getElementById("auth-status");

    if (!email || !password) return (status.textContent = "❌ Both fields required.");
    if (!email.includes("@") || !email.includes(".")) return (status.textContent = "❌ Invalid email.");
    if (password.length < 6) return (status.textContent = "❌ Password ≥ 6 characters.");

    const res = await fetch("/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    status.textContent = data.message;
  }

  async function login() {
    const email = document.getElementById("auth-email")?.value.trim();
    const password = document.getElementById("auth-password")?.value.trim();
    const status = document.getElementById("auth-status");

    if (!email || !password) return (status.textContent = "❌ Both fields required.");

    const res = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    status.textContent = data.message;
    if (res.ok) window.location.href = "/";
  }

  async function logout() {
    const res = await fetch("/logout");
    const data = await res.json();
    alert(data.message);
    window.location.href = "/login";
  }

  // =============== LOCATION & MAP =================
  let selectedLatLng = null;

  if (document.getElementById("map")) {
    const mapHint = document.getElementById("map-hint");
    const map = L.map("map").setView([20.5937, 78.9629], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap France",
    }).addTo(map);

    map.on("click", async function (e) {
      selectedLatLng = e.latlng;

      if (mapHint) mapHint.style.display = "none"; // hide message on interaction

      map.eachLayer(layer => {
        if (layer instanceof L.Marker) map.removeLayer(layer);
      });

      L.marker(selectedLatLng).addTo(map)
        .bindPopup(`📍 Selected: ${selectedLatLng.lat}, ${selectedLatLng.lng}`)
        .openPopup();

      document.getElementById("lat").value = selectedLatLng.lat;
      document.getElementById("lng").value = selectedLatLng.lng;

      try {
        const response = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${selectedLatLng.lat}&lon=${selectedLatLng.lng}&format=json`);
        const data = await response.json();
        document.getElementById("location").value = data.display_name || `Lat: ${selectedLatLng.lat}, Lng: ${selectedLatLng.lng}`;
      } catch {
        document.getElementById("location").value = `Lat: ${selectedLatLng.lat}, Lng: ${selectedLatLng.lng}`;
      }
    });

    map.on("dragstart", () => {
      if (mapHint) mapHint.style.display = "none"; // hide on drag too
    });
  }

  // ================== FAQ Toggle ====================
  document.querySelectorAll(".faq-header")?.forEach(header => {
    header.addEventListener("click", function () {
      const item = this.parentElement;
      const answer = item.querySelector(".faq-answer");
      const toggle = item.querySelector(".faq-toggle");

      item.classList.toggle("open");
      if (item.classList.contains("open")) {
        answer.style.maxHeight = answer.scrollHeight + "px";
        answer.style.opacity = 1;
        toggle.textContent = "−";
      } else {
        answer.style.maxHeight = 0;
        answer.style.opacity = 0;
        toggle.textContent = "+";
      }
    });
  });

  // ================= ID VERIFICATION ==================
  const verifyForm = document.getElementById("verify-form");
  if (verifyForm) {
    verifyForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const formData = new FormData(this);
      const statusEl = document.getElementById("verify-status");
      const reportForm = document.getElementById("report-form");

      statusEl.style.color = "blue";
      statusEl.textContent = "⏳ Verifying identity...";

      try {
        const res = await fetch("/verify-identity", { method: "POST", body: formData });
        const data = await res.json();
        if (res.ok && data.status === "verified") {
          statusEl.style.color = "green";
          statusEl.textContent = data.message;
          reportForm.style.display = "block";
        } else {
          statusEl.style.color = "red";
          statusEl.textContent = data.message;
          reportForm.style.display = "none";
        }
      } catch (err) {
        statusEl.style.color = "red";
        statusEl.textContent = "❌ Server error. Try again.";
      }
    });
  }

  // =============== REPORT ISSUE ====================
  const reportForm = document.getElementById("report-form");
  if (reportForm) {
    reportForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const title = document.getElementById("title").value.trim();
      const desc = document.getElementById("description").value.trim();
      const category = document.getElementById("category").value;
      const location = document.getElementById("location").value.trim();

      if (!title || !desc || !category) {
        alert("❌ Fill all fields before submitting.");
        return;
      }

      const data = {
        title,
        description: desc,
        category,
        location,
        latitude: selectedLatLng?.lat || null,
        longitude: selectedLatLng?.lng || null,
      };

      try {
        const res = await fetch("/report-issue", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        const result = await res.json();
        if (res.ok) {
          alert(result.message);
          loadIssues();
        } else {
          alert(result.message);
        }
      } catch {
        alert("❌ Submission error.");
      }
    });
  }

  // ================= LOAD ISSUES ===================
  async function loadIssues() {
    const res = await fetch("/get-issues");
    const data = await res.json();
    const issueList = document.getElementById("issue-list");
    if (!issueList) return;

    issueList.innerHTML = "";
    data.issues.forEach(issue => {
      const card = document.createElement("div");
      card.classList.add("card", "issue-card");
      card.innerHTML = `
        <h3>${issue.title}</h3>
        <p>${issue.description}</p>
        <p><strong>Category:</strong> ${issue.category}</p>
        <p><strong>Location:</strong> ${issue.location}</p>
        <p><strong>Status:</strong> ${issue.status}</p>
        <div class="vote-section">
          <button class="upvote-btn" data-issue-id="${issue.id}" ${issue.upvoted ? "disabled style='opacity:0.6'" : ""}>👍</button>
          <span class="vote-count">${issue.upvotes}</span> Upvotes
        </div>
      `;
      issueList.appendChild(card);
    });

    document.querySelectorAll(".upvote-btn").forEach(btn => {
      const issueId = btn.dataset.issueId;

      btn.addEventListener("click", async function () {
        const res = await fetch("/upvote-issue", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ issue_id: issueId }),
        });

        const data = await res.json();
        if (res.ok) {
          this.nextElementSibling.textContent = data.upvotes;
          this.disabled = true;
          this.style.opacity = 0.6;
        } else {
          alert(data.message);
        }
      });
    });
  }

  loadIssues();

  // ✅ Global access for login.html
  window.register = register;
  window.login = login;
  window.logout = logout;
});
