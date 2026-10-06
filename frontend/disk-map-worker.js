/* Fixed local validation worker. No imported path is opened or executed. */
importScripts("model-assets/bundled.js", "disk-map-model.js");
self.onmessage = (event) => {
  const { ticket } = event.data;
  try {
    let text = event.data.text;
    if (event.data.bytes !== undefined) {
      try {
        text = new TextDecoder("utf-8", { fatal: true }).decode(event.data.bytes);
      } catch (_) {
        throw new self.DiskMapModel.ImportError("The export is not valid UTF-8 text.");
      }
    }
    const accepted = self.DiskMapModel.parse(text, self.DiskMapAssets.schema);
    self.postMessage({ ticket, accepted });
  } catch (error) {
    self.postMessage({
      ticket,
      error:
        error instanceof self.DiskMapModel.ImportError
          ? error.message
          : "The export could not be validated.",
    });
  }
};
