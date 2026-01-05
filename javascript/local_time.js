const now = new Date();

const monthSelect = document.getElementById('month');
const yearInput = document.getElementById('year');

let month = (now.getMonth()) + 1 // getMonth() is zero based
let year = now.getFullYear();

// alwasy display last month
if (month == 1) {
    year = year - 1
    month = 12
} else {
    month -= 1
}

monthSelect.value = month;
yearInput.value = year;
