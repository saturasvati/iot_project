async function get_settings() {
    let host = window.location.host;
    let url = "http://" + host + "/api/get/settings";
    let request = new Request(url);
    let response = await fetch(request);
    if (response.ok) {
        let response_json = response.json();
        return response_json
    } else {
        throw new Error("Host doesn't answer");
    }
}

function init_ui(response) {
    response.then(result => {
        document.getElementById("border_inf_temperature").value = result["temperature"]["inf"];
        document.getElementById("border_sup_temperature").value = result["temperature"]["sup"];
        document.getElementById("border_inf_humidity").value = result["humidity"]["inf"];
        document.getElementById("border_sup_humidity").value = result["humidity"]["sup"];
        document.getElementById("border_acceptable_co2").value = result["co2"]["acceptable"];
        document.getElementById("border_harmful_co2").value = result["co2"]["harmful"];
        document.getElementById("border_danger_co2").value = result["co2"]["danger"];
        document.getElementById("period_report").value = result["period"]["forecast"]/60;
        document.getElementById("period_forecast").value = result["period"]["report"]/60;
    });
}

function send_settings() {
    let temperature_inf = document.getElementById("border_inf_temperature").value;
    let temperature_sup = document.getElementById("border_sup_temperature").value;
    let humidity_inf = document.getElementById("border_inf_humidity").value;
    let humidity_sup = document.getElementById("border_sup_humidity").value;
    let co2_acceptable = document.getElementById("border_acceptable_co2").value;
    let co2_harmful = document.getElementById("border_harmful_co2").value;
    let co2_danger = document.getElementById("border_danger_co2").value;
    let period_report = Number(document.getElementById("period_report").value)*60;
    let period_forecast = Number(document.getElementById("period_forecast").value)*60;
    let new_settings = {
        "temperature": {
            "inf": temperature_inf,
            "sup": temperature_sup,
        },
        "humidity": {
            "inf": humidity_inf,
            "sup": humidity_sup,
        },
        "co2": {
            "acceptable": co2_acceptable,
            "harmful": co2_harmful,
            "danger": co2_danger,
        },
        "period": {
            "report": period_report,
            "forecast": period_forecast,
        },
    }
    let host = window.location.host;
    let url = "http://" + host + "/api/common/settings";
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(new_settings) });
}


let response;

function init() {
    response = get_settings();
    init_ui(response);
}