# User Guide

Deskmate lets you create a demo workspace and sign in and out. Requesters submit tickets and read their workspace's knowledge-base articles. Support Officers read and resolve their workspace's tickets, highlight a ticket's key sentences with SoC LLM, write and edit its knowledge-base articles, create Requester accounts and reset Requester passwords.

Its home page shows the heading **Deskmate**, this text and a **Sign in** link:

> Deskmate is under construction.

## Getting accounts

Choose **Sign in** on the home page, or go to `/sign-in/`. Below the sign-in form, the page shows:

> No account? Create a demo workspace with 2 Requesters and 1 Support Officer.

Press **Create demo workspace**. A new workspace is created, and a page headed **Demo workspace created** shows these lines, a table and a **Sign in** link:

> Workspace: *code*
>
> Copy these passwords now. They will not be shown again.

The table's **Username**, **Role** and **Password** columns list the workspace's two Requesters, `requester1-`*code* and `requester2-`*code*, and its Support Officer, `support1-`*code*, where *code* is the workspace's code from the first line.

The new workspace also starts with two sample articles and three sample tickets, which you see after signing in. Both roles' **Knowledge base** lists show, earliest first:

- **Fix a printer that will not print**
- **Connect to the office Wi-Fi**

Both roles' **Tickets** lists show, earliest first, these tickets, whose pages show their status:

- **Printer will not print**: **Closed**, with the saved answer under **Reply**
- **Wi-Fi keeps disconnecting**: **Open**
- **Need a spreadsheet app**: **Open**

From then on, they are ordinary articles and tickets of that workspace, and the rest of this guide applies to them as to any other.

Creating a workspace signs no one in. Press **Sign in** to go to the sign-in page.

Pressing **Create demo workspace** again, or reloading the page and resending the form, creates another workspace, with new usernames and passwords and its own copies of the sample articles and tickets.

## Signing in

On `/sign-in/`, enter your **Username** and **Password**, and press **Sign in**.

Usernames use only ASCII letters, digits and `@`, `.`, `+`, `-`, `_`; surrounding whitespace is ignored and letter case must match (see [ACC-1.7](../workflow/specs/product/accounts.md#acc-1-sign-in-and-out-by-role)). Passwords must match exactly, including letter case and spaces.

If the username or password is wrong or empty, the page shows:

> Incorrect username or password.

The username you typed stays in its field, and the password field is empty.

## Your role's page

After signing in, you land on your role's page:

- a Requester on `/requester/`, headed **Requester**;
- a Support Officer on `/support/`, headed **Support Officer**.

Both role pages show the same line directly below the heading, as do their ticket, knowledge-base, Requester-password-reset and Requester-account-creation pages, including validation errors and results:

> Workspace: *code*

**Workspace: unavailable** means the stored accounts do not identify one canonical demo workspace code (see [ACC-1.2](../workflow/specs/product/accounts.md#acc-1-sign-in-and-out-by-role)). On your role's page, this comes before the following line and the **Sign out** button:

> Signed in as *your username*.

Press **Sign out** to sign out and go back to the sign-in page.

While signed in, `/sign-in/` takes you to your role's page. While signed out, a role's page takes you to the sign-in page.

You are signed out 8 hours after signing in, however active you are. Closing your browser may also sign you out, but not if it reopens your previous tabs, so press **Sign out** on a shared computer.

## Creating a Requester account

As a Support Officer, choose **Create Requester account** on your role's page. The form shows:

> Create one Requester account in this workspace.

Press **Create account**. On success, **Requester account created** shows a table with **Username** and **Password** columns and this message:

> Copy this password now. It will not be shown again.

The new account gets the next numbered username, starting with `requester3-`*code*, and preserves your workspace's code. The workspace can hold 20 Requesters in total, including its initial two. The new Requester can sign in with the displayed credentials; you stay signed in.

Choose **Support Officer** to return to your role's page. Reopening the form shows no credentials. Submitting again creates another account when permitted. If the response fails or is lost after creation, the account may already exist and its password cannot be recovered; another submission may create another account.

At the workspace's Requester limit, the form shows:

> This workspace already has 20 Requester accounts.

Otherwise, if its stored accounts do not identify a canonical workspace, it shows:

> Requester accounts cannot be created for this workspace.

These rejections create no account. See [ACC-5](../workflow/specs/product/accounts.md#acc-5-create-a-requester-in-the-current-workspace) for the complete rules.

## Resetting a Requester's password

As a Support Officer, choose **Reset Requester password** on your role's page. Enter the Requester's **Username** and press **Reset password**.

On success, **Requester password reset** shows a table with **Username** and **Password** columns and this message:

> Copy this password now. It will not be shown again.

The Requester can sign in with the new password. Their old password no longer works, and their earlier sessions require sign-in on their next visit to a page that requires it. You stay signed in.

Choose **Support Officer** to return to your role's page. Reopening the form shows no password; submitting again performs another reset.

An invalid username or an account that is not a Requester in your workspace leaves you on the form with:

> No Requester with that username was found in your workspace.

See [ACC-4](../workflow/specs/product/accounts.md#acc-4-reset-a-requesters-password) for the complete rules.

## Knowledge base

As a Support Officer, choose **Knowledge base** on your role's page. The list shows your workspace's article titles, or **No articles yet.**

Choose **New article**, enter **Title** and **Body**, then press **Save article**. The saved article opens under **Edit article**. Select an article title from **Knowledge base** to reopen and edit it.

Articles use plain text. Titles must be unique within your workspace, ignoring case and surrounding whitespace. Any Support Officer in that workspace can edit its articles. A successful later save replaces both fields, including changes submitted from an older open form.

Validation errors keep you on the form with your input and show the relevant message:

> Enter a valid title (1 to 200 characters).
>
> Enter a valid body (1 to 10000 characters).
>
> An article with this title already exists.

## Reading articles

As a Requester, choose **Knowledge base** on your role's page. The list shows your workspace's article titles, or **No articles yet.** Choose a title to read the article; **Knowledge base** takes you back to the list.

Articles are plain text. The reading page shows an article's title and body as saved, with its line breaks.

## Tickets

As a Requester, choose **Tickets** on your role's page. The list shows your workspace's tickets, earliest first, or **No tickets yet.**

Choose **New ticket**, enter **Title** and **Description**, then press **Submit ticket**. The new ticket opens under **Ticket**, showing **Open** and its saved text; **Tickets** takes you back to the list. Tickets are plain text, and their line breaks are shown.

Before submitting, you can press **Suggest articles** on the same form. The draft's title and description are sent to SoC LLM, which suggests search phrases; articles in your workspace whose saved title or body contains one of those phrases appear under **Suggested articles**, earliest first, up to three titles linking to their reading pages. Article bodies and the phrases themselves are not shown, and matching is best effort rather than a verified solution. Deskmate does not save your draft or the suggestions, though it may count the request toward the AI limit and keep an audit record; the form keeps your draft so **Submit ticket** still works.

While waiting, **Suggest articles** changes to **Suggesting...** and is disabled, and **Suggesting articles...** appears immediately below the form. Your field values, earlier suggestions, messages and validation errors stay visible, and **Submit ticket** remains enabled.

Any returned form shows **Suggest articles** and **Submit ticket** enabled again, without the loading message. Submitting **Submit ticket**, or browser validation stopping submission, shows no suggestion loading feedback. If scripting is unavailable, both buttons submit normally without loading feedback.

The suggestion result may show **No matching articles found.**, **Article suggestions are unavailable. Try again later.** or **AI limit reached. Try again later.**

Tickets need not have unique titles: each valid submission creates a new ticket. Validation errors keep you on the form with your input and show the relevant message:

> Enter a valid title (1 to 200 characters).
>
> Enter a valid description (1 to 10000 characters).

As a Support Officer, choose **Tickets** on your role's page. Your list shows every ticket in your workspace, earliest first, or **No tickets yet.** Choose a title to open **Ticket**, showing its saved title and description and its stored status, **Open** or **Closed**. Choose **Tickets** to return to your list, or **Support Officer** on the list to return to your role's page.

Opening or refreshing ticket lists and detail pages changes no ticket.

As a Support Officer, choose **Resolve ticket** on an **Open** ticket to open the separate **Resolve ticket** form. Enter a **Reply**, then press **Resolve ticket**. Choose **Ticket** to return without submitting.

A successful submission opens **Ticket**, showing **Closed** and the saved answer under **Reply**. Requesters and Support Officers in the workspace see the same reply as plain text with its line breaks. A ticket without a saved reply has no **Reply** heading.

**Reply** is required. Invalid input stays in the form with:

> Enter a valid reply (1 to 10000 characters).

A closed ticket has no **Resolve ticket** link. Repeated submissions, including from an older open form, keep the first saved answer. There are no controls to edit the reply or reopen the ticket.

As a Support Officer, press **Highlight key sentences** on an **Open** or **Closed** ticket. Highlighting sends its description to SoC LLM to select up to three copied passages; matching occurrences may also be highlighted, while the complete original description stays visible. Selection is best effort.

The result is temporary: opening the ticket again from **Tickets** shows no highlights or result message and makes no AI request. Press **Highlight key sentences** again to request a new result.

The result may show **No key sentences found.**, **Key sentences are unavailable. Try again later.** or **AI limit reached. Try again later.**

See [RQ-2](../workflow/specs/product/tickets.md#rq-2-read-workspace-tickets-as-a-support-officer), [RQ-3](../workflow/specs/product/tickets.md#rq-3-resolve-a-ticket-with-a-reply) and [RQ-4](../workflow/specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences) for the complete rules and limits.

## Forbidden pages

A page headed **Forbidden** shows one line. If you open the other role's page, it says:

> This page is not for your role.

If you submit a form that has expired, it says:

> This form has expired. Go back, reload the page and try again.

## Too many attempts

After too many sign-in attempts, workspace or Requester account creations, or password resets in a short time, from your internet address or from everyone, a page headed **Too many attempts** shows one line instead. If you pressed **Sign in**, it says:

> Too many sign-in attempts. Wait a few minutes, then try again.

If you pressed **Create demo workspace**, it says:

> Too many demo workspaces have been created. Wait a few minutes, then try again.

If you pressed **Create account**, it says:

> Too many account creation attempts. Wait a few minutes, then try again.

If you pressed **Reset password**, it says:

> Too many password resets. Wait a few minutes, then try again.

Demo workspace and Requester account creations share one allowance: 3 attempts from your address group or 5 from everyone in the preceding 10 minutes. Rejections for the workspace quota or invalid membership count toward it. Sign-in and reset allowances are separate; see [ACC-3](../workflow/specs/product/accounts.md#acc-3-rate-limit-signing-in-and-creating-demo-workspaces) and [ACC-5](../workflow/specs/product/accounts.md#acc-5-create-a-requester-in-the-current-workspace) for the complete rules.

If you are already signed in, you stay signed in, and your role's page and **Sign out** work as usual.
