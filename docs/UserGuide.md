# User Guide

Deskmate is still being built. So far you can only create a demo workspace, then sign in and out with its accounts.

Its home page shows only the heading **Deskmate** and this line:

> Deskmate is under construction.

## Getting accounts

Go to `/sign-in/`; the home page does not link to it. Below the sign-in form, the page shows:

> No account? Create a demo workspace with 2 Requesters and 1 Support Officer.

Press **Create demo workspace**. A new workspace is created, and a page headed **Demo workspace created** shows this line, a table and a **Sign in** link:

> Copy these passwords now. They will not be shown again.

The table's **Username**, **Role** and **Password** columns list the workspace's two Requesters, `requester1-`*code* and `requester2-`*code*, and its Support Officer, `support1-`*code*, where *code* is the same in all three.

Creating a workspace signs no one in. Press **Sign in** to go to the sign-in page.

Pressing **Create demo workspace** again, or reloading the page and resending the form, creates another workspace, with new usernames and passwords.

## Signing in

On `/sign-in/`, enter your **Username** and **Password**, and press **Sign in**.

If the username or password is wrong or empty, the page shows:

> Incorrect username or password.

The username you typed stays in its field, and the password field is empty.

## Your role's page

After signing in, you land on your role's page:

- a Requester on `/requester/`, headed **Requester**;
- a Support Officer on `/support/`, headed **Support Officer**.

The page shows this line and a **Sign out** button:

> Signed in as *your username*.

Press **Sign out** to sign out and go back to the sign-in page.

While signed in, `/sign-in/` takes you to your role's page. While signed out, a role's page takes you to the sign-in page.

You are signed out 8 hours after signing in, however active you are. Closing your browser may also sign you out, but not if it reopens your previous tabs, so press **Sign out** on a shared computer.

## Forbidden pages

A page headed **Forbidden** shows one line. If you open the other role's page, it says:

> This page is not for your role.

If you submit a form that has expired, it says:

> This form has expired. Go back, reload the page and try again.

## Too many attempts

After too many sign-in attempts or workspace creations in a short time, from your internet address or from everyone, a page headed **Too many attempts** shows one line instead. If you pressed **Sign in**, it says:

> Too many sign-in attempts. Wait a few minutes, then try again.

If you pressed **Create demo workspace**, it says:

> Too many demo workspaces have been created. Wait a few minutes, then try again.

If you are already signed in, you stay signed in, and your role's page and **Sign out** work as usual.
