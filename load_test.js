import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
  vus: __ENV.VUS ? parseInt(__ENV.VUS) : 10,
  duration: __ENV.DURATION || '10s',
};

export default function () {
  http.get(__ENV.TARGET_URL);
  sleep(1);
}
