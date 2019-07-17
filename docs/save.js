function saveAs(filename, text) {
  try {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();
    document.body.removeChild(element);
  } catch (e) {
    alert("Tu explorador no soporta esta funcionalidad");
  }
}
