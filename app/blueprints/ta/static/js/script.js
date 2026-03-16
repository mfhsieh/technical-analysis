"use strict";

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("chart-form");
    const overlay = document.getElementById("loading-overlay");

    if (form && overlay) {  // submit listener
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            event.stopPropagation();

            const isValid = form.checkValidity();
            form.classList.add("was-validated");

            if (!isValid) {
                if (!overlay.classList.contains("d-none")) overlay.classList.add("d-none");
                return
            }

            overlay.classList.remove("d-none");  // 顯示 overlay

            setTimeout(() => {  // 確保 overlay 有時間顯示
                const checkedIndicators = form.querySelectorAll('input[name="indicators"][type="checkbox"]:checked');
                const selectedIndicators = [];

                checkedIndicators.forEach(checkbox => {
                    selectedIndicators.push(checkbox.value);
                    checkbox.disabled = true
                });
                const indicators = selectedIndicators.join(",");

                let hiddenInput = form.querySelector('input[name="indicators"][type="hidden"]');
                if (!hiddenInput) {
                    hiddenInput = document.createElement("input");
                    hiddenInput.type = "hidden";
                    hiddenInput.name = "indicators";
                    form.appendChild(hiddenInput);
                }
                hiddenInput.value = indicators;

                form.submit();
            }, 50);

        }, false);
    }

    const allIndicators = form.querySelectorAll('input[name="indicators"][type="checkbox"]');
    const selectAllBtn = document.getElementById("select-all-indicators");  // "全選" button
    if (selectAllBtn) {
        selectAllBtn.addEventListener("click", function () {
            allIndicators.forEach(checkbox => checkbox.checked = true);
        });
    }

    const deselectAllBtn = document.getElementById("deselect-all-indicators");  // "全不選" button
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener("click", function () {
            allIndicators.forEach(checkbox => checkbox.checked = false);
        });
    }

    const chartTitle = document.getElementById("chart-title");
    if (chartTitle) { /* scroll into view logic */
        setTimeout(() => {
            chartTitle.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 500);
    }

    window.addEventListener("pageshow", function (event) { /* bfcache handling */
        if (event.persisted) {

            const currentOverlay = document.getElementById("loading-overlay");
            if (currentOverlay && !currentOverlay.classList.contains("d-none")) {
                currentOverlay.classList.add("d-none");
            }

            const currentForm = document.getElementById("chart-form");
            if (currentForm) {
                currentForm
                    .classList.remove("was-validated");

                currentForm
                    .querySelectorAll('input[name="indicators"][type="checkbox"]:disabled')
                    .forEach(checkbox => checkbox.disabled = false);

                const oldHidden = currentForm.querySelector('input[name="indicators"][type="hidden"]');
                if (oldHidden) {
                    oldHidden.remove();
                }
            }
        }
    });

    // Hide overlay when Bokeh is ready
    if (overlay && !overlay.classList.contains("d-none")) {
        const checkBokeh = setInterval(() => {
            if (window.Bokeh && window.Bokeh.index && Object.keys(window.Bokeh.index).length > 0) {
                overlay.classList.add("d-none");
                clearInterval(checkBokeh);
            }
        }, 100);

        // Safety timeout (10 seconds)
        setTimeout(() => clearInterval(checkBokeh), 10000);
    }
});

function adjusted_x_range(x_start, x_end, X_MIN, X_MAX, XRANGE_MIN, XRANGE_MAX) {  // 用於 x range 及 slider 的輔助函數
    const x_interval = Math.max(XRANGE_MIN, Math.min(XRANGE_MAX, Math.abs(x_end - x_start)));
    const x_middle = (x_start + x_end) / 2;

    x_start = x_middle - x_interval / 2;
    x_end = x_middle + x_interval / 2;

    if (x_end > X_MAX) {
        x_end = X_MAX;
        x_start = x_end - x_interval;
    } else if (x_start < X_MIN) {
        x_start = X_MIN;
        x_end = x_start + x_interval;
    }

    return [parseFloat(x_start.toFixed(3)), parseFloat(x_end.toFixed(3))];  // 避免因小數誤差的循環
}

function is_within_epsilon(num1, num2, epsilon) {  // 用於 x range 及 slider 的輔助函數
    return Math.abs(num1 - num2) <= Math.abs(epsilon);
}
