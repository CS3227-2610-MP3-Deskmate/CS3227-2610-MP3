# User Guide

Deskmate lets you create a demo workspace and sign in and out. Support Officers can also write and edit knowledge-base articles and reset Requester passwords in their workspace.

Its home page shows the heading **Deskmate**, this text and a **Sign in** link:

> Deskmate is under construction.

## Getting accounts

Choose **Sign in** on the home page, or go to `/sign-in/`. Below the sign-in form, the page shows:

> No account? Create a demo workspace with 2 Requesters and 1 Support Officer.

Press **Create demo workspace**. A new workspace is created, and a page headed **Demo workspace created** shows this line, a table and a **Sign in** link:

> Copy these passwords now. They will not be shown again.

The table's **Username**, **Role** and **Password** columns list the workspace's two Requesters, `requester1-`*code* and `requester2-`*code*, and its Support Officer, `support1-`*code*, where *code* is the same in all three.

Creating a workspace signs no one in. Press **Sign in** to go to the sign-in page.

Pressing **Create demo workspace** again, or reloading the page and resending the form, creates another workspace, with new usernames and passwords.

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

The page shows this line and a **Sign out** button:

> Signed in as *your username*.

Press **Sign out** to sign out and go back to the sign-in page.

While signed in, `/sign-in/` takes you to your role's page. While signed out, a role's page takes you to the sign-in page.

You are signed out 8 hours after signing in, however active you are. Closing your browser may also sign you out, but not if it reopens your previous tabs, so press **Sign out** on a shared computer.

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

## Forbidden pages

A page headed **Forbidden** shows one line. If you open the other role's page, it says:

> This page is not for your role.

If you submit a form that has expired, it says:

> This form has expired. Go back, reload the page and try again.

## Too many attempts

After too many sign-in attempts, workspace creations or password resets in a short time, from your internet address or from everyone, a page headed **Too many attempts** shows one line instead. If you pressed **Sign in**, it says:

> Too many sign-in attempts. Wait a few minutes, then try again.

If you pressed **Create demo workspace**, it says:

> Too many demo workspaces have been created. Wait a few minutes, then try again.

If you pressed **Reset password**, it says:

> Too many password resets. Wait a few minutes, then try again.

If you are already signed in, you stay signed in, and your role's page and **Sign out** work as usual.
