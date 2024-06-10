
import asyncio
import logging

import aiohttp
import urllib3
from aiohttp import BasicAuth

urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class JiraException(Exception):
    pass


class Jira(object):
    def __init__(
        self,
        url,
        username,
        ticket_queue,
        password=None,
        token=None,
        loop=None,
    ):
        try:
            logger.debug(":Initializing Jira object:")
            self.url = url
            self.username = username
            self.ticket_queue = ticket_queue
            self.password = password
            if not loop:
                self.loop = asyncio.new_event_loop()
                self.new_loop = True
            else:
                self.loop = loop
                self.new_loop = False
            self.token = token
            if not self.token:
                if self.password:
                    payload = BasicAuth(self.username, self.password)
                else:
                    logger.error(
                        "Basic Authentication expected as no token was found but password is missing"
                    )
                    raise JiraException
            else:
                payload = "Bearer: %s" % self.token
            self.headers = {"Authorization": payload}
        except:
            pass

    def __exit__(self):
        if self.new_loop:
            self.loop.close()

    async def get_request(self, endpoint):
        logger.debug("GET: %s" % endpoint)
        try:
            async with aiohttp.ClientSession(
                headers=self.headers,
                loop=self.loop,
            ) as session:
                async with session.get(
                    self.url + endpoint,
                    verify_ssl=False,
                ) as response:
                    result = await response.json(content_type="application/json")
        except Exception as ex:
            logger.debug(ex)
            logger.error("There was something wrong with your request.")
            return None
        if response.status == 404:
            logger.error("Resource not found: %s" % self.url + endpoint)
            return None
        return result

    async def post_request(self, endpoint, payload):
        logger.debug("POST: {%s:%s}" % (endpoint, payload))
        try:
            async with aiohttp.ClientSession(
                headers=self.headers, loop=self.loop
            ) as session:
                async with session.post(
                    self.url + endpoint,
                    json=payload,
                    verify_ssl=False,
                ) as response:
                    data = await response.json(content_type="application/json")
        except Exception as ex:
            logger.debug(ex)
            logger.error("There was something wrong with your request.")
            return False
        if response.status in [200, 201, 204]:
            logger.info("Post successful.")
            return data
        if response.status == 404:
            logger.error("Resource not found: %s" % self.url + endpoint)
        return False

    async def put_request(self, endpoint, payload):
        logger.debug("POST: {%s:%s}" % (endpoint, payload))
        try:
            async with aiohttp.ClientSession(
                headers=self.headers, loop=self.loop
            ) as session:
                async with session.put(
                    self.url + endpoint,
                    json=payload,
                    verify_ssl=False,
                ) as response:
                    await response.json(content_type="application/json")
        except Exception as ex:
            logger.debug(ex)
            logger.error("There was something wrong with your request.")
            return False
        if response.status in [200, 201, 204]:
            logger.info("Post successful.")
            return True
        if response.status == 404:
            logger.error("Resource not found: %s" % self.url + endpoint)
        return False

    async def create_ticket(self, summary, description):
        endpoint = "/issue/"
        logger.debug("POST new ticket")
        short_summary = summary.split('\r')
        title = f"{short_summary[0]}"

        data = {
            "fields": {
                "project": {"key": self.ticket_queue},
                "issuetype": {"name": "Task"},
                "summary": title,
                "description": description,
            }
        }
        response = await self.post_request(endpoint, data)
        return response

    async def create_subtask(self, parent_ticket, cloud, description, type_of_subtask):
        endpoint = "/issue/"
        logger.debug("POST new subtask")
        title = f"{cloud} {type_of_subtask}"

        data = {
            "fields": {
                "project": {"key": self.ticket_queue},
                "issuetype": {"id": "5"},
                "parent": {"key": f"{self.ticket_queue}-{parent_ticket}"},
                "summary": title,
                "labels": [type_of_subtask.upper()],
                "description": description,
            }
        }
        response = await self.post_request(endpoint, data)
        return response

    async def add_watcher(self, ticket, watcher):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s/watchers" % issue_id
        logger.debug("POST transition: {%s:%s}" % (issue_id, watcher))
        response = await self.post_request(endpoint, watcher)
        return response

    async def add_label(self, ticket, label):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s" % issue_id
        data = {"update": {"labels": [{"add": label}]}}
        response = await self.put_request(endpoint, data)
        return response

    async def post_comment(self, ticket, comment):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s/comment" % issue_id
        payload = {"body": comment}
        response = await self.post_request(endpoint, payload)
        return response

    async def post_transition(self, ticket, transition):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s/transitions" % issue_id
        payload = {"transition": {"id": transition}}
        response = await self.post_request(endpoint, payload)
        return response

    async def get_transitions(self, ticket):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s/transitions" % issue_id
        result = await self.get_request(endpoint)
        if not result:
            logger.error("Failed to get transitions")
            return []

        transitions = result.get("transitions")
        if transitions:
            return transitions
        else:
            logger.error("No transitions found under %s" % issue_id)
            return []

    async def get_ticket(self, ticket):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s" % issue_id
        result = await self.get_request(endpoint)
        if not result:
            logger.error("Failed to get ticket")
            return None
        return result

    async def get_watchers(self, ticket):
        issue_id = "%s-%s" % (self.ticket_queue, ticket)
        endpoint = "/issue/%s/watchers" % issue_id
        logger.debug("GET watchers: %s" % endpoint)
        result = await self.get_request(endpoint)
        if not result:
            logger.error("Failed to get watchers")
            return None
        return result

    async def get_user_by_email(self, email):
        endpoint = f"/user/search?username={email}"
        logger.debug("GET user: %s" % endpoint)
        result = await self.get_request(endpoint)
        if not result:
            logger.error("User not found")
            return None
        for user in result:
            if user.get("emailAddress") == email:
                return user
        return None

    async def get_pending_tickets(self):
        query = {"statusCategory": 4, "labels": "EXTENSION"}
        logger.debug("GET pending tickets")
        result = await self.search_tickets(query)
        if not result:
            logger.error("Failed to get pending tickets")
            return None
        return result

    async def search_tickets(self, query=None):
        project = {"project": self.ticket_queue}
        prefix = "/search?jql="
        query_items = []

        if not query:
            query = project
        else:
            query.update(project)

        for k, v in query.items():
            query_items.append(f"{k}={v}")

        jql = " AND ".join(query_items)
        endpoint = f"{prefix}{jql}"
        logger.debug("GET pending tickets: %s" % endpoint)
        result = await self.get_request(endpoint)
        if not result:
            logger.error("Failed to get pending tickets")
            return None
        return result
