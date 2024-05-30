async function get_stats() {
    let host = window.location.host;
    let url = "http://" + host + "/api/get/device_status";
    let request = new Request(url);
    let response = await fetch(request);
    if (response.ok) {
        let response_json = response.json();
        return response_json
    } else {
        throw new Error("Host doesn't answer");
    }
}

let executor_field_prefix = [
    "executor_on",
    "executor_autocontrol",
    "executor_setting",
    "executor_token",
    "executor_address",
];

let executor_noun = [
    "ac",
    "vent",
    "heater",
    "humidifier",
];

let sensor_prefix = [
    "sensor_remove",
    "sensor_new_token",
]

let sensor_noun = [
    "temperature",
    "humidity",
    "co2",
    "temperature_outer",
    "humidity_outer",
]

function init_ui(response) {
    response.then(result => {
        for (const prefix of executor_field_prefix) {
            for (const noun of executor_noun) {
                let element = document.getElementById(prefix + "_" + noun);
                switch (element.getAttribute("type")) {
                    case "checkbox":
                        switch (result[prefix][noun]) {
                            case true:
                                element.checked = true;
                                console.log(prefix, noun, element.checked);
                                break;
                            case false:
                                element.checked = false;
                                console.log(prefix, noun, element.checked);
                                break;
                        }
                        break;
                    case "text":
                        element.setAttribute("value", result[prefix][noun]);
                        break;
                }
            }
        }
    });
}

function send_device_settings(response) {
    let new_settings = {};
    for (const prefix of executor_field_prefix) new_settings[prefix] = {};
    response.then(result => {
        for (const prefix of executor_field_prefix) {
            for (const noun of executor_noun) {
                let element = document.getElementById(prefix + "_" + noun);
                let value = null;
                switch (prefix) {
                    case "executor_on":
                        value = element.checked;
                        if (value != result[prefix][noun]) { new_settings[prefix][noun] = value };
                        break;
                    case "executor_autocontrol":
                        value = element.checked;
                        if (value != result[prefix][noun]) { new_settings[prefix][noun] = value };
                        console.log(prefix, noun, result[prefix][noun], new_settings[prefix][noun], value);
                        break;
                    case "executor_setting":
                        value = element.value;
                        if (value != result[prefix][noun] && value !== "") { new_settings[prefix][noun] = value };
                        break;
                    case "executor_token":
                        value = element.value;
                        if (value !== "") { new_settings[prefix][noun] = value };
                        break;
                    case "executor_address":
                        value = element.value;
                        if (value != result[prefix][noun] && value !== "") { new_settings[prefix][noun] = value };
                        break;
                }
            }
        }
        let host = window.location.host;
        let url = "http://" + host + "/api/device/settings";
        fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(new_settings) });
    });
}

function send_sensor_settings() {
    let new_settings = {};
    for (const prefix of sensor_prefix) new_settings[prefix] = {};
    for (const prefix of sensor_prefix) {
        for (const noun of sensor_noun) {
            let element = document.getElementById(prefix + "_" + noun);
            // console.log(element,prefix + "_" + noun);
            console.log(element, prefix, noun, element.checked);
            switch (prefix) {
                case "sensor_remove":
                    if (element.checked) { new_settings[prefix][noun] = element.checked };
                    break;
                case "sensor_new_token":
                    if (element.value !== "") { new_settings[prefix][noun] = element.value };
                    break;
            }
        }
    }
    let host = window.location.host;
    let url = "http://" + host + "/api/device/settings";
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(new_settings) });
}

function send_manually_request() {
    let value = document.getElementById("manually_value").value;
    let token = document.getElementById("manually_token").value;
    let host = window.location.host;
    let url = "http://" + host + "/api/device/send";
    fetch(url, { method: "POST", body: JSON.stringify({ "Auth": token, "value": value }), headers: { "Content-Type": "application/json" } });
}

let response;

function init() {
    response = get_stats();
    init_ui(response);
}