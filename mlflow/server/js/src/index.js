import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './components/App';
import registerServiceWorker from './registerServiceWorker';
import { setupCsrf } from './setupCsrf';
import { Provider } from 'react-redux';
import store from './Store';
import $ from 'jquery';
window.$ = $;

setupCsrf();

const root = (
  <Provider store={store}>
    <App/>
  </Provider>
);
ReactDOM.render(root, document.getElementById('root'));

registerServiceWorker();
