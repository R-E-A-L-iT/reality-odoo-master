function changeStyle() {
    var tabs = document.getElementsByClassName("var_radio_label")
    for(var i = 0; i < tabs.length; i++) {
        var radio = document.getElementById(tabs[i].for)
        if(radio.checked == true){
            tabs[i].setAttribute("class", "var_radio_label selected" )
        } else {
            tabs[i].setAttribute("class", "var_radio_label")
        }
    }
}
