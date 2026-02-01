import axios from 'axios';
import { getAccessToken, refreshAccessToken, clearTokens } from './auth';

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
};

const apiClient = axios.create();

apiClient.interceptors.request.use(
  async (config) => {
    if (config.skipAuth) {
      return config;
    }

    let token = getAccessToken();
    if (!token) {
      token = await refreshAccessToken();
    }

    if (token) {
      // eslint-disable-next-line no-param-reassign
      config.headers = config.headers || {};
      // eslint-disable-next-line no-param-reassign
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const originalRequest = error.config || {};
    if (error.response?.status !== 401 || originalRequest.skipAuth) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      clearTokens();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          if (!token) {
            throw error;
          }
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${token}`;
          originalRequest._retry = true;
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    return new Promise((resolve, reject) => {
      refreshAccessToken()
        .then((newToken) => {
          if (!newToken) {
            clearTokens();
            reject(error);
            return;
          }
          processQueue(null, newToken);
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          resolve(apiClient(originalRequest));
        })
        .catch((refreshError) => {
          processQueue(refreshError, null);
          clearTokens();
          reject(refreshError);
        })
        .finally(() => {
          isRefreshing = false;
        });
    });
  }
);

export default apiClient;
