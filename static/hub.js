document.addEventListener("DOMContentLoaded", () => {
  // ✅ Hamburger dropdown logic
  const dropbtn = document.querySelector(".dropbtn");
  const dropdownContent = document.querySelector(".dropdown-content");

  if (dropbtn && dropdownContent) {
    dropbtn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdownContent.classList.toggle("show");
    });

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".dropdown")) {
        dropdownContent.classList.remove("show");
      }
    });
  }

  // ✅ FAQ toggle logic
  const faqToggles = document.querySelectorAll(".faq-toggle");
  faqToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const answer = toggle.closest(".faq-item").querySelector(".faq-answer");
      if (answer) {
        answer.style.display = answer.style.display === "block" ? "none" : "block";
        toggle.textContent = answer.style.display === "block" ? "-" : "+";
      }
    });
  });

  // ✅ Identity verification → report form toggle
  const verifyForm = document.getElementById("verify-form");
  const reportForm = document.getElementById("report-form");
  const verifyStatus = document.getElementById("verify-status");

  if (verifyForm && reportForm) {
    verifyForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(verifyForm);

      try {
        const res = await fetch("/verify-identity", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        verifyStatus.textContent = data.message;
        verifyStatus.style.color = res.ok ? "green" : "red";

        if (res.ok) {
          verifyForm.style.display = "none";
          reportForm.style.display = "block";
        }
      } catch (err) {
        verifyStatus.textContent = "❌ Server error during verification.";
        verifyStatus.style.color = "red";
      }
    });
  }

  // ✅ Report issue submission
  if (reportForm) {
    reportForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const payload = {
        title: document.getElementById("title").value.trim(),
        description: document.getElementById("description").value.trim(),
        location: document.getElementById("location").value.trim(),
        latitude: document.getElementById("lat")?.value,
        longitude: document.getElementById("lng")?.value,
        category: document.getElementById("category").value,
      };

      const res = await fetch("/report-issue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      alert(data.message);
      if (res.ok) reportForm.reset();
    });
  }

  // ✅ Load issues in track.html
  const issueList = document.getElementById("issue-list");
  if (issueList) {
    fetch("/get-issues")
      .then((res) => res.json())
      .then((data) => {
        data.issues.forEach((issue) => {
          const card = document.createElement("div");
          card.className = "card status-card";
          card.innerHTML = `
            <h3>${issue.title}</h3>
            <p>Status: <span class="status">${issue.status}</span></p>
            <p>👍 ${issue.upvotes} Upvotes</p>
            ${
              issue.upvoted
                ? `<button disabled>Already Upvoted</button>`
                : `<button onclick="upvote(${issue.id}, this)">Upvote</button>`
            }
          `;
          issueList.appendChild(card);
        });
      });
  }

  // ✅ Initialize Leaflet Map with Reverse Geocoding
  const mapContainer = document.getElementById("map");

  if (mapContainer) {
    var map = L.map("map").setView([12.9716, 77.5946], 13); // Default location

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    let marker;

    map.on("click", async function (event) {
      const { lat, lng } = event.latlng;

      if (marker) {
        marker.setLatLng([lat, lng]);
      } else {
        marker = L.marker([lat, lng]).addTo(map);
      }

      document.getElementById("lat").value = lat;
      document.getElementById("lng").value = lng;

      // ✅ Reverse Geocoding to Autofill Address
      try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`);
        const data = await res.json();
        document.getElementById("location").value = data.display_name || "Address not found";
      } catch (error) {
        console.error("Reverse geocoding failed:", error);
        document.getElementById("location").value = "Error fetching address";
      }
    });
  }
});

// ✅ Handle Upvote
async function upvote(issueId, btn) {
  const res = await fetch("/upvote-issue", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ issue_id: issueId }),
  });

  const data = await res.json();
  alert(data.message);
  if (res.ok) {
    btn.disabled = true;
    btn.innerText = "Already Upvoted";
  }
}
