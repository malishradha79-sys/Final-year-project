
// =================================
// Display Current Date
// =================================

function displayDate() {
    const dateElement = document.getElementById("current-date");

    if (dateElement) {
        const today = new Date();

        const options = {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric"
        };

        dateElement.textContent =
            today.toLocaleDateString("en-IN", options);
    }
}

displayDate();


// =================================
// Existing Button Events
// =================================

const aiButton = document.querySelector(".ai-box button");

if (aiButton) {
    aiButton.addEventListener("click", function() {
        alert("AI Financial Assistant is coming soon!");
    });
}

const viewAllButton = document.querySelector(".section-heading button");

if (viewAllButton) {
    viewAllButton.addEventListener("click", function() {
        alert("Transaction management will be available soon!");
    });
}


// =================================
// Expense Analytics Chart
// =================================

async function loadExpenseChart() {

    const canvas = document.getElementById("expenseChart");

    if (!canvas) {
        console.error("Expense chart canvas not found!");
        return;
    }

    if (typeof Chart === "undefined") {
        console.error("Chart.js library is not loaded!");
        return;
    }

    try {

        const response = await fetch("/api/expense-summary");

        if (!response.ok) {
            throw new Error("Expense API failed");
        }

        const expenses = await response.json();

        console.log("Expense data:", expenses);

        const categories = expenses.map(item => item.category);
        const amounts = expenses.map(item => Number(item.total));

        if (window.expenseChartInstance) {
            window.expenseChartInstance.destroy();
        }

        if (expenses.length === 0) {
            canvas.parentElement.innerHTML =
                "<p>No expense data available yet.</p>";
            return;
        }

        window.expenseChartInstance = new Chart(canvas, {
            type: "doughnut",

            data: {
                labels: categories,

                datasets: [{
                    label: "Expenses",
                    data: amounts,
                    backgroundColor: [
                        "#37d69a",
                        "#ff9f43",
                        "#6c63ff",
                        "#ff6384",
                        "#36a2eb",
                        "#f4d35e"
                    ],
                    borderWidth: 2
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: true,
                        position: "bottom"
                    }
                }
            }
        });

        console.log("Expense chart created successfully!");

    } catch (error) {
        console.error("Expense chart error:", error);
    }
}

loadExpenseChart();

console.log("FinTrack AI JavaScript loaded successfully!");
document.querySelectorAll(".budget-progress-fill").forEach(function(bar) {
    const progress = Number(bar.dataset.progress) || 0;
    bar.style.width = Math.min(Math.max(progress, 0), 100) + "%";
});

// AI Financial Assistant Chat

const aiChatForm = document.getElementById("ai-chat-form");

if (aiChatForm) {

    const aiInput = document.getElementById("ai-user-input");
    const chatMessages = document.getElementById("chat-messages");
    const sendButton = document.getElementById("ai-send-button");

    function addChatMessage(message, className) {

        const messageDiv = document.createElement("div");
        messageDiv.className = className;

        const paragraph = document.createElement("p");
        paragraph.textContent = message;

        messageDiv.appendChild(paragraph);
        chatMessages.appendChild(messageDiv);

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    aiChatForm.addEventListener("submit", async function(event) {

        event.preventDefault();

        const userMessage = aiInput.value.trim();

        if (!userMessage) {
            return;
        }

        addChatMessage(userMessage, "user-message");

        aiInput.value = "";
        sendButton.disabled = true;
        sendButton.textContent = "Thinking...";

        try {

            const response = await fetch("/ai-chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: userMessage
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.reply || "Unable to get AI response.");
            }

            addChatMessage(data.reply, "ai-message");

        } catch (error) {

            addChatMessage(
                "Sorry, something went wrong. Please try again.",
                "ai-message"
            );

            console.error("AI Chat Error:", error);

        } finally {

            sendButton.disabled = false;
            sendButton.textContent = "Send";
            aiInput.focus();

        }

    });

}

// Smart Spending Insights
const insightsButton = document.getElementById("generate-insights-btn");
const insightsContainer = document.getElementById("insights-container");

if (insightsButton && insightsContainer) {
    insightsButton.addEventListener("click", async function () {
        insightsButton.disabled = true;
        insightsButton.textContent = "Analysing...";
        insightsContainer.textContent = "Please wait while FinTrack AI analyses your finances...";

        try {
            const response = await fetch("/api/smart-insights");
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to generate insights.");
            }

            insightsContainer.replaceChildren();

            const insightsText = document.createElement("p");
            insightsText.textContent = data.insights;
            insightsContainer.appendChild(insightsText);

        } catch (error) {
            insightsContainer.textContent =
                "Sorry, unable to generate insights. Please try again.";
            console.error("Smart Insights Error:", error);

        } finally {
            insightsButton.disabled = false;
            insightsButton.textContent = "Generate Insights";
        }
    });
}
// Financial Goals Progress Bars

document.querySelectorAll(".goal-progress-fill").forEach(function(bar) {
    const progress = Number(bar.dataset.progress) || 0;

    bar.style.width = Math.min(Math.max(progress, 0), 100) + "%";
});