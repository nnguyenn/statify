(() => {
  const overlay = document.getElementById('alertOverlay');
  if (!overlay) return;

  const modal   = overlay.querySelector('.alert-modal');
  const titleEl = overlay.querySelector('#alertTitle');
  const msgEl   = overlay.querySelector('#alertMsg');
  const okBtn   = overlay.querySelector('#alertOk');
  const closeBtn= overlay.querySelector('#alertClose');

  function cleanup(){
    overlay.hidden = true;
    overlay.setAttribute('aria-hidden','true');
    document.body.classList.remove('modal-open');
    overlay.removeEventListener('click', onBackdrop);
    document.removeEventListener('keydown', onEsc);
    okBtn.onclick = null;
    closeBtn.onclick = null;
  }
  function onBackdrop(e){ if (e.target === overlay) cleanup(); }
  function onEsc(e){ if (e.key === 'Escape') cleanup(); }

  function open(opts = {}){
    const { title='Heads up', message='', okText='OK', onOk=null } = opts;
    titleEl.textContent = title;
    msgEl.textContent   = message;
    okBtn.textContent   = okText;

    overlay.hidden = false;
    overlay.removeAttribute('aria-hidden');
    document.body.classList.add('modal-open');
    okBtn.focus();

    okBtn.onclick = () => { cleanup(); if (onOk) onOk(); };
    closeBtn.onclick = cleanup;
    overlay.addEventListener('click', onBackdrop);
    document.addEventListener('keydown', onEsc);
  }

  // expose
  window.showAlert  = open;
  window.hideAlert  = cleanup;
  window.showError  = (msg, title='Something went wrong') => open({title, message: msg});
})();
