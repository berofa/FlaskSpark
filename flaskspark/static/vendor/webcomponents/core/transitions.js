/**
 * Run a callback once the node's CSS transition finished.
 *
 * Completes immediately when no transition applies (e.g. prefers-reduced-
 * motion) and falls back to a timer in case transitionend never fires.
 */
export function afterTransition(node, done) {
  const duration = Number.parseFloat(getComputedStyle(node).transitionDuration || "0") * 1000;
  if (!duration) {
    done();
    return;
  }
  let finished = false;
  const finish = () => {
    if (finished) {
      return;
    }
    finished = true;
    node.removeEventListener("transitionend", finish);
    done();
  };
  node.addEventListener("transitionend", finish);
  window.setTimeout(finish, duration + 50);
}
