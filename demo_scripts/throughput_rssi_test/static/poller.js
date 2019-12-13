function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// Continously requests the last updates.
async function fetch_data() {
    while(true) {
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
              if (this.readyState == 4 && this.status == 200) {
                postMessage(xhttp.responseText)
              }
        }
        xhttp.open("GET", "devices", true);
        xhttp.send();

        await sleep(250)
    }
}

fetch_data();
