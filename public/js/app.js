let auth0Client = null;

const fetchAuthConfig = () => fetch('/auth_config.json');

const configureClient = async () => {
  const response = await fetchAuthConfig();
  const config = await response.json();

  // Create the Auth0 client. Use authorizationParams to set redirect URI to current origin
  auth0Client = await auth0.createAuth0Client({
    domain: config.domain,
    clientId: config.clientId,
    authorizationParams: {
      redirect_uri: "http://127.0.0.1"
    }
  });
};

window.addEventListener('load', async () => {
  await configureClient();

  // Update UI for initial state
  await updateUI();

  // Handle redirect back from Auth0 (if present)
  const query = window.location.search;
  if (query.includes('code=') && query.includes('state=')) {
    console.log(query);
    try {
      await auth0Client.handleRedirectCallback();
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (e) {
      console.error('Error handling redirect callback', e);
    }
  }

  const isAuthenticated = await auth0Client.isAuthenticated();
  if (isAuthenticated) {
    console.log(isAuthenticated);
    // show the gated content
    onAuthenticated();
    USER_ID = await auth0Client.getTokenSilently();
    console.log(JSON.stringify(await auth0Client.getUser()));
  }
});

const updateUI = async () => {
  if (!auth0Client) return;
  const isAuthenticated = await auth0Client.isAuthenticated();

  // Match IDs used in index.html
  const loginBtn = document.getElementById('loginBtn');
  const logoutBtn = document.getElementById('logoutBtn');
  const continueBtn = document.getElementById('continueBtn');

  if (loginBtn) loginBtn.disabled = isAuthenticated;
  if (logoutBtn) logoutBtn.disabled = !isAuthenticated;
  if (continueBtn) continueBtn.disabled = !isAuthenticated;
};

// Called when we detect the user is authenticated
const onAuthenticated = async () => {
  try {
    const user = await auth0Client.getUser();
    // populate UI with user info if present
    const userName = document.getElementById('userName');
    const userInfo = document.getElementById('userInfo');
    if (userName && user) userName.textContent = user.name || user.email || user.sub || 'Signed in';
    if (userInfo) userInfo.style.display = 'block';

    // hide overlay and start app's feed
    if (typeof hideOverlayAndStart === 'function') hideOverlayAndStart();
  } catch (e) {
    console.error('Failed to get user info', e);
  }
  await updateUI();
};

// Public functions used by the page
const login = async () => {
  if (!auth0Client) return;
  await auth0Client.loginWithRedirect();
};

const logout = () => {
  if (!auth0Client) return;
  // Stop all videos before logging out
  if (typeof stopAllVideos === 'function') stopAllVideos();
  // Remove hidden class from login overlay
  const loginOverlay = document.getElementById('loginOverlay');
  if (loginOverlay) loginOverlay.classList.remove('hidden');
  // Hide corner logout button
  const cornerLogout = document.getElementById('cornerLogout');
  if (cornerLogout) cornerLogout.style.display = 'none';
  auth0Client.logout({ logoutParams: { returnTo: window.location.origin } });
};

// Hook up buttons if present (safe to call multiple times)
const hookAuthButtons = () => {
  const loginBtn = document.getElementById('loginBtn');
  const logoutBtn = document.getElementById('logoutBtn');
  const continueBtn = document.getElementById('continueBtn');

  if (loginBtn) {
    loginBtn.onclick = (e) => { e.preventDefault(); login(); };
  }
  if (logoutBtn) {
    logoutBtn.onclick = (e) => { e.preventDefault(); logout(); };
  }
  if (continueBtn) {
    continueBtn.onclick = (e) => { e.preventDefault(); if (typeof hideOverlayAndStart === 'function') hideOverlayAndStart(); };
  }
};

// Try to hook buttons on script load (and again after DOM ready in case)
hookAuthButtons();
document.addEventListener('DOMContentLoaded', hookAuthButtons);

