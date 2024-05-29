class TranslateAssassment {
    constructor(src, dst, accents, class_name) {
        this.src = src;
        this.dst = dst;
        this.accents = accents;
        this.class_name = class_name;
    }

    find() {
        return document.getElementsByClassName(this.class_name);
    }

    substitute() {
        let elements = this.find();
        for (let i = 0; i < elements.length; i++) {
            let element = elements[i];
            let old_label = element.innerText;
            let index = this.src.indexOf(old_label);
            let new_label = this.dst[index];
            let accent_label = this.accents[index];
            element.innerText = new_label;
            element.classList.add(accent_label);
        }
    }
}

function translate_assessments() {
    translate_assessment_temperature = new TranslateAssassment(
        ["tooLow", "optimum", "tooHigh"],
        ["холодно", "комфортно", "жарко"],
        ["accent_cold", "accent_good", "accent_hot"],
        "assessment_temperature");
    translate_assessment_humidity = new TranslateAssassment(
        ["tooLow", "optimum", "tooHigh"],
        ["холодно", "комфортно", "жарко"],
        ["accent_cold", "accent_good", "accent_hot"],
        "assessment_humidity");
    translate_assessment_co2 = new TranslateAssassment(
        ["optimum", "acceptable", "harmful", "danger"],
        ["комфортно", "допустимо", "вредно", "опасно"],
        ["accent_good", "accent_warning", "accent_danger", "accent_danger"],
        "assessment_co2");
    translate_assessment_temperature.substitute();
    translate_assessment_humidity.substitute();
    translate_assessment_co2.substitute();
}

function timedelta(date, shift) {
    let src_timestamp = date.valueOf();
    let dst_timestamp = src_timestamp + shift;
    let dst = new Date(dst_timestamp);
    return dst
}

function make_plot() {
    let period = Number(document.getElementById("plot_period_selector").value) * 3600;
    let field = document.getElementById("plot_field_selector").value;

    let units;
    let title;
    switch (field) {
        case "temperature":
            units = "°C";
            title = "Температура";
            break;
        case "temperature_outer":
            units = "°C";
            title = "Температура (на улице)";
            break;
        case "humidity":
            units = "%";
            title = "Влажность";
            break;
        case "humidity_outer":
            units = "%";
            title = "Влажность (на улице)";
            break;
        case "co2":
            units = "ppm";
            title = "Концентрация углекислого газа";
            break;
    }

    let layout = {
        title: title,
        yaxis: {
            title: units,
        }
    }

    let host = window.location.host;
    let url = "http://" + host + "/api/get/data" + "?period=" + period;
    let request = new Request(url);
    let raw_data = new Set;
    let data;
    let x_array = [];
    let y_array = [];
    fetch(request)
        .then((response) => {
            if (response.status === 200) {
                return response.json();
            } else {
                throw new Error("Host doesn't answer");
            }
        })
        .then((response) => {
            raw_data = response[field];
            for (let i = 0; i < raw_data.length; i++) {
                x_array[i] = new Date(raw_data[i]["date"]).toISOString();
                y_array[i] = Number(raw_data[i][field]);
            }
            data = { x: x_array, y: y_array };
            console.log(data);
            Plotly.newPlot("plot_area", [data], layout);
        });

}

function init() {
    translate_assessments();
    make_plot();
}