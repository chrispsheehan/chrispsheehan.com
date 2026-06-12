function handler(event) {
  var request = event.request;
  var uri = request.uri;

  if (!uri.match(/\.[a-zA-Z0-9]+$/)) {
    request.uri = '/index.html';
  }

  return request;
}
